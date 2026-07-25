`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 07/24/2026 10:52:39 AM
// Design Name: 
// Module Name: blink
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module blink(
    input wire clk,
    output wire led
    );
    
    reg [26:0] counter = 0;
    
    always @(posedge clk) begin
        counter <= counter + 1;
    end
    
    assign led = counter[26];    // toggles ~once per second at 125 MHz
endmodule
