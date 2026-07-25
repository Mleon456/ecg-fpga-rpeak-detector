# ECG FPGA R-Peak Detector

Real-time ECG acquisition and signal processing pipeline combining an STM32
microcontroller front-end with FPGA-accelerated feature extraction on a
Zybo Z7-10 (Zynq-7010 SoC).

## Project Overview

This project acquires a live ECG signal from body-surface electrodes,
digitizes and filters it on an STM32 microcontroller, and streams the result
to a PC for visualization. The next phase of the project moves R-peak
detection — the core algorithm for calculating heart rate from an ECG
waveform — onto the Zybo Z7-10's FPGA fabric as a hardware-accelerated,
streaming Verilog pipeline, rather than computing it in software.

The goal is to demonstrate a complete signal chain spanning analog signal
acquisition, embedded systems firmware, digital signal processing, and
custom RTL design — with the FPGA doing genuine parallel hardware
computation, not just running code on an ARM core.

## Architecture
Electrodes (AD8232) → STM32 ADC → Digital HPF (baseline wander removal)
→ UART → PC (live Python visualization)
→ [in progress] Zybo Z7-10 FPGA → R-peak detection → heart rate

## Current Status

- ✅ **Hardware acquisition** — SparkFun AD8232 wired to a NUCLEO-F446RE
  (STM32F446RE), sampling ECG via ADC1 at 250 Hz
- ✅ **Digital filtering (STM32)** — single-pole IIR high-pass filter
  (α ≈ 0.9876, 0.5 Hz cutoff) implemented in embedded C for baseline
  wander removal
- ✅ **Live visualization** — Python (pyserial + matplotlib) dual-plot
  display of raw and filtered ECG in real time, with leads-off detection
- ✅ **FPGA toolchain validated** — Zybo Z7-10 confirmed working end-to-end:
  Verilog → Vivado synthesis/implementation → bitstream → JTAG programming
  → physical LED blink test (`led_test/`)
- 🔲 **FPGA R-peak detection (in progress)** — Verilog RTL implementation
  of a Pan-Tompkins-style QRS/R-peak detection pipeline on the Zynq PL fabric

## Repository Structure
stm32_firmware/ STM32CubeIDE project — ADC acquisition, IIR filtering,
UART streaming (main.c, HAL drivers, .ioc config)
python_visualization/ Live serial plotting script (raw + filtered ECG)
led_test/ Toolchain validation: LED blink test on Zybo Z7-10
iir_filter/ (planned) FPGA R-peak detection RTL, testbenches
docs/ Project notes and documentation

## Hardware

- **MCU**: STM32 NUCLEO-F446RE
- **ECG front-end**: SparkFun AD8232 (single-lead ECG sensor breakout)
- **Electrodes**: 3M Red Dot pads — RA (black), LA (blue), RL/reference (red)
- **FPGA**: Digilent Zybo Z7-10 (Xilinx/AMD Zynq-7010 SoC, XC7Z010-1CLG400C)

## Software / Tools

- STM32CubeMX / STM32CubeIDE (firmware)
- Python (pyserial, matplotlib) for live visualization
- Vivado (Verilog RTL, synthesis, implementation, hardware programming)

## Signal Pipeline Details

**Acquisition**: ECG signal sampled via STM32 ADC1 at 250 Hz, referenced to
STM32 GPIO leads-off detection pins (LO+/LO−) from the AD8232.

**Filtering**: A single-pole IIR high-pass filter removes baseline wander
(slow signal drift from respiration/movement), implemented directly in
firmware: y[n] = α × (y[n-1] + x[n] - x[n-1])

with α ≈ 0.9876 giving a ~0.5 Hz cutoff at a 250 Hz sample rate.

**Streaming**: Filtered and raw samples are sent over UART as CSV
(`adc_value, filtered_value, lo_plus, lo_minus`) and rendered live in a
dual-subplot Python display.

## Roadmap

- [ ] Implement Pan-Tompkins-style R-peak detection as Verilog RTL on the
      Zybo Z7-10's PL fabric, streaming data over UART from the STM32
- [ ] Add a low-pass filtering stage for additional noise reduction
- [ ] Simulate and verify the FPGA pipeline in testbenches before hardware
      deployment
- [ ] Real-time heart rate calculation and display
- [ ] Stretch: arrhythmia detection (tachycardia/bradycardia flags)

## Getting Started

**STM32 firmware**: Open `stm32_firmware/ECG_Monitor` in STM32CubeIDE,
build, and flash to a NUCLEO-F446RE.

**Visualization**: 
```bash
pip install pyserial matplotlib
python python_visualization/ecg_live_plot.py
```
Update `SERIAL_PORT` in the script to match your board's COM port.

**FPGA blink test**: Open Vivado, create a new RTL project targeting the
Zybo Z7-10 board, add `led_test/src/blink.v` and
`led_test/constraints/blink.xdc`, then run synthesis → implementation →
generate bitstream → program device.

## License

See [LICENSE](LICENSE).
