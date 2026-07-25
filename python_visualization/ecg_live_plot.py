"""
Live ECG Visualization
Reads CSV data (adc_value,filtered_value,lo_plus,lo_minus) from the STM32 over
USART/serial and plots both the raw and high-pass filtered waveforms in real
time using matplotlib.

Setup:
    pip install pyserial matplotlib

Usage:
    1. Update SERIAL_PORT below to match your board (e.g. "COM6" on Windows,
       or "/dev/ttyACM0" / "/dev/tty.usbmodemXXXX" on Mac/Linux)
    2. Close Tera Term / any other program using that COM port first —
       only one program can hold a serial port open at a time.
    3. Run: python ecg_live_plot.py
"""

import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque

# ---- Configuration ----
SERIAL_PORT = "COM6"      # <-- change this to match your board's port
BAUD_RATE = 115200
WINDOW_SIZE = 500          # how many samples to show on screen at once

# ---- Setup serial connection ----
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

# ---- Data buffers ----
adc_values = deque([2048] * WINDOW_SIZE, maxlen=WINDOW_SIZE)       # raw
filtered_values = deque([0.0] * WINDOW_SIZE, maxlen=WINDOW_SIZE)   # high-pass filtered
leads_off = deque([False] * WINDOW_SIZE, maxlen=WINDOW_SIZE)

# ---- Plot setup: two stacked subplots (raw on top, filtered on bottom) ----
fig, (ax_raw, ax_filt) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

line_raw, = ax_raw.plot(adc_values, color="lime", linewidth=1)
ax_raw.set_ylim(0, 4095)          # full ADC range (12-bit)
ax_raw.set_xlim(0, WINDOW_SIZE)
ax_raw.set_facecolor("black")
ax_raw.set_title("Raw ECG (unfiltered)", color="white")
ax_raw.set_ylabel("ADC Value (raw)", color="white")
ax_raw.tick_params(colors="white")

line_filt, = ax_filt.plot(filtered_values, color="cyan", linewidth=1)
ax_filt.set_ylim(-200, 200)       # tune this if your peaks clip or look too small
ax_filt.set_xlim(0, WINDOW_SIZE)
ax_filt.set_facecolor("black")
ax_filt.set_title("Filtered ECG (baseline wander removed)", color="white")
ax_filt.set_xlabel("Sample", color="white")
ax_filt.set_ylabel("Filtered Value", color="white")
ax_filt.tick_params(colors="white")

fig.patch.set_facecolor("black")
fig.tight_layout()

status_text = ax_raw.text(
    0.02, 0.95, "", transform=ax_raw.transAxes,
    color="red", fontsize=12, fontweight="bold", va="top"
)


def read_serial_data():
    """Read and parse one line of CSV data from the serial port."""
    try:
        raw_line = ser.readline().decode("utf-8", errors="ignore").strip()
        if not raw_line:
            return None
        parts = raw_line.split(",")
        if len(parts) != 4:
            return None
        adc_val = int(parts[0])
        filt_val = float(parts[1])
        lo_plus = parts[2] == "1"
        lo_minus = parts[3] == "1"
        return adc_val, filt_val, (lo_plus or lo_minus)
    except (ValueError, UnicodeDecodeError):
        # Malformed line (can happen if we catch a partial line at startup) — skip it
        return None


def update(frame):
    # Drain all available lines this frame so the plot doesn't lag behind real time
    while ser.in_waiting > 0:
        result = read_serial_data()
        if result is not None:
            adc_val, filt_val, off = result
            adc_values.append(adc_val)
            filtered_values.append(filt_val)
            leads_off.append(off)

    line_raw.set_ydata(adc_values)
    line_raw.set_xdata(range(len(adc_values)))

    line_filt.set_ydata(filtered_values)
    line_filt.set_xdata(range(len(filtered_values)))

    if leads_off[-1]:
        status_text.set_text("LEADS OFF - check electrode contact")
        line_raw.set_color("gray")
        line_filt.set_color("gray")
    else:
        status_text.set_text("")
        line_raw.set_color("lime")
        line_filt.set_color("cyan")

    return line_raw, line_filt, status_text


ani = FuncAnimation(fig, update, interval=20, blit=False, cache_frame_data=False)

try:
    plt.show()
finally:
    ser.close()
