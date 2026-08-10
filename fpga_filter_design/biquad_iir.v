//=============================================================
// biquad_iir.v
//
// Reusable Direct Form II biquad (2nd-order IIR filter) core.
// Instantiate this module once per filter stage -- e.g. once
// with high-pass coefficients (baseline wander removal), once
// with notch coefficients (60 Hz mains rejection) -- and cascade
// the two instances together.
//
// Difference equations implemented (Direct Form II):
//   w[n] = x[n] - a1*w[n-1] - a2*w[n-2]     (feedback path)
//   y[n] = b0*w[n] + b1*w[n-1] + b2*w[n-2]  (feedforward path)
//
// Fixed-point format: Q2.14 (2 integer bits incl. sign,
// 14 fractional bits) for coefficients, matching the values
// produced by design_ecg_iir_filters.py.
//
// Timing model: this design assumes the sample rate is much
// slower than the clock (250 Hz samples vs. a 125 MHz clock,
// here), so the whole multiply-add chain is done combinationally
// in a single cycle and only latched on sample_valid. No
// pipelining -- there's no throughput problem to justify it at
// this sample rate.
//=============================================================

module biquad_iir #(
    parameter DATA_WIDTH = 16,     // sample width, signed
    parameter COEF_WIDTH = 16,     // coefficient width, signed
    parameter FRAC_BITS  = 14,     // Q2.14 fixed point
    parameter signed [COEF_WIDTH-1:0] B0 = 0,
    parameter signed [COEF_WIDTH-1:0] B1 = 0,
    parameter signed [COEF_WIDTH-1:0] B2 = 0,
    parameter signed [COEF_WIDTH-1:0] A1 = 0,
    parameter signed [COEF_WIDTH-1:0] A2 = 0
)(
    input  wire                          clk,
    input  wire                          rst,           // synchronous, active high
    input  wire                          sample_valid,   // pulse: x_in is a new sample
    input  wire signed [DATA_WIDTH-1:0]  x_in,
    output reg  signed [DATA_WIDTH-1:0]  y_out,
    output reg                           y_valid
);

    // Delay registers: w[n-1], w[n-2]. This is the entire
    // internal state of the filter -- only 2 registers, which
    // is the whole point of using Direct Form II.
    reg signed [DATA_WIDTH-1:0] w1, w2;

    // Full-width products (sample x coefficient), still in
    // Q2.14 scale before we shift back down.
    wire signed [DATA_WIDTH+COEF_WIDTH-1:0] a1_mult, a2_mult;
    wire signed [DATA_WIDTH+COEF_WIDTH-1:0] b0_mult, b1_mult, b2_mult;

    // Products after shifting back down to plain integer
    // sample scale.
    wire signed [DATA_WIDTH-1:0] a1_term, a2_term;
    wire signed [DATA_WIDTH-1:0] b0_term, b1_term, b2_term;

    // w_next carries one extra guard bit to absorb the
    // subtraction below before truncating back to DATA_WIDTH.
    wire signed [DATA_WIDTH:0] w_next;

    // ---- Feedback path: w[n] = x[n] - a1*w1 - a2*w2 ----
    assign a1_mult = A1 * w1;
    assign a2_mult = A2 * w2;
    assign a1_term = a1_mult >>> FRAC_BITS;
    assign a2_term = a2_mult >>> FRAC_BITS;
    assign w_next  = x_in - a1_term - a2_term;

    // ---- Feedforward path: y[n] = b0*w[n] + b1*w1 + b2*w2 ----
    assign b0_mult = B0 * w_next[DATA_WIDTH-1:0];
    assign b1_mult = B1 * w1;
    assign b2_mult = B2 * w2;
    assign b0_term = b0_mult >>> FRAC_BITS;
    assign b1_term = b1_mult >>> FRAC_BITS;
    assign b2_term = b2_mult >>> FRAC_BITS;

    always @(posedge clk) begin
        if (rst) begin
            w1      <= 0;
            w2      <= 0;
            y_out   <= 0;
            y_valid <= 1'b0;
        end else if (sample_valid) begin
            // Shift the delay chain and latch the new output,
            // exactly one clock after a new sample arrives.
            w2      <= w1;
            w1      <= w_next[DATA_WIDTH-1:0];
            y_out   <= b0_term + b1_term + b2_term;
            y_valid <= 1'b1;
        end else begin
            y_valid <= 1'b0;
        end
    end

endmodule


//=============================================================
// Example top-level instantiation: cascading the high-pass and
// notch stages using the SAME reusable biquad_iir module,
// each with its own coefficient set.
//
// Coefficients below are the Q2.14 values from
// design_ecg_iir_filters.py:
//   High-pass: b = [16239, -32478, 16239], a = [1, -32477, 16095]
//   Notch:     b = [15982, -2007, 15982],  a = [1, -2007, 15580]
// (a0 is always 1 and isn't needed as a multiplier.)
//=============================================================

module ecg_filter_pipeline #(
    parameter DATA_WIDTH = 16
)(
    input  wire                          clk,
    input  wire                          rst,
    input  wire                          sample_valid,
    input  wire signed [DATA_WIDTH-1:0]  x_in,
    output wire signed [DATA_WIDTH-1:0]  y_out,
    output wire                          y_valid
);

    wire signed [DATA_WIDTH-1:0] hp_out;
    wire                         hp_valid;

    // Stage 1: high-pass, removes baseline wander
    biquad_iir #(
        .DATA_WIDTH(DATA_WIDTH),
        .B0(16'sd16239), .B1(-16'sd32478), .B2(16'sd16239),
        .A1(-16'sd32477), .A2(16'sd16095)
    ) u_highpass (
        .clk(clk),
        .rst(rst),
        .sample_valid(sample_valid),
        .x_in(x_in),
        .y_out(hp_out),
        .y_valid(hp_valid)
    );

    // Stage 2: notch, removes 60 Hz interference.
    // Feeds directly from the high-pass stage's output --
    // same module, different coefficients.
    biquad_iir #(
        .DATA_WIDTH(DATA_WIDTH),
        .B0(16'sd15982), .B1(-16'sd2007), .B2(16'sd15982),
        .A1(-16'sd2007), .A2(16'sd15580)
    ) u_notch (
        .clk(clk),
        .rst(rst),
        .sample_valid(hp_valid),
        .x_in(hp_out),
        .y_out(y_out),
        .y_valid(y_valid)
    );

endmodule
