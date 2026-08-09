"""
Design IIR filter coefficients for the ECG FPGA pipeline.

Stage 1 of the FPGA filter build: design in floating point, then check
stability, then generate fixed-point coefficients ready to drop into
Verilog multipliers.

Two filters, each a single biquad (2nd-order section):
  1. High-pass @ 0.5 Hz  -> removes baseline wander
  2. Notch    @ 60 Hz    -> removes power-line interference

Both are designed with scipy.signal, which does the analog-to-digital
bilinear transform for you -- same math you hand-derived for the
single-pole filter, just handled by a library and for a proper 2nd-order
section instead of a 1st-order one.
"""

import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

FS = 250.0  # sample rate in Hz, matches your STM32 ADC loop

# -----------------------------------------------------------------------
# 1. DESIGN IN FLOATING POINT
# -----------------------------------------------------------------------

# High-pass, 0.5 Hz cutoff, 2nd-order Butterworth.
# order=2 -> maximally flat passband, one biquad section.
hp_sos = signal.butter(N=2, Wn=0.5, btype='highpass', fs=FS, output='sos')

# Notch at 60 Hz. Q controls how narrow the notch is -- higher Q means it
# only bites the 60 Hz line and leaves nearby ECG content untouched.
notch_b, notch_a = signal.iirnotch(w0=60.0, Q=30.0, fs=FS)
notch_sos = signal.tf2sos(notch_b, notch_a)

print("=" * 60)
print("HIGH-PASS (baseline wander removal, 0.5 Hz cutoff)")
print("=" * 60)
print("SOS section [b0, b1, b2, a0, a1, a2]:")
print(hp_sos)

print()
print("=" * 60)
print("NOTCH (60 Hz power-line interference)")
print("=" * 60)
print("SOS section [b0, b1, b2, a0, a1, a2]:")
print(notch_sos)

# -----------------------------------------------------------------------
# 2. STABILITY CHECK -- poles must stay inside the unit circle
# -----------------------------------------------------------------------
# a[0] is always normalized to 1, so we check the roots of the a
# coefficients (denominator) for each section.


def check_stability(sos, name):
    print(f"\nStability check: {name}")
    stable = True
    for section in sos:
        a = section[3:6]  # [a0, a1, a2], a0 == 1
        poles = np.roots(a)
        mags = np.abs(poles)
        print(f"  pole magnitudes: {mags}")
        if np.any(mags >= 1.0):
            stable = False
    print(f"  -> {'STABLE' if stable else 'UNSTABLE -- do not build this'}")
    return stable


check_stability(hp_sos, "high-pass")
check_stability(notch_sos, "notch")

# -----------------------------------------------------------------------
# 3. FIXED-POINT QUANTIZATION (Q2.14 example -- adjust to your headroom)
# -----------------------------------------------------------------------
# Q2.14 means 2 integer bits (including sign) + 14 fractional bits,
# 16-bit total. Coefficients here are all well under 2.0 in magnitude,
# so this format has margin. Re-check ranges if you change filter type.

FRAC_BITS = 14
SCALE = 2 ** FRAC_BITS


def to_fixed_point(sos, name):
    print(f"\nFixed-point coefficients ({name}), Q2.14, scale={SCALE}:")
    fixed_sections = []
    for section in sos:
        b = section[0:3]
        a = section[3:6]
        b_fixed = np.round(b * SCALE).astype(int)
        a_fixed = np.round(a * SCALE).astype(int)
        fixed_sections.append((b_fixed, a_fixed))
        print(f"  b (numerator)   : {b} -> {b_fixed}")
        print(f"  a (denominator) : {a} -> {a_fixed}")
    return fixed_sections


hp_fixed = to_fixed_point(hp_sos, "high-pass")
notch_fixed = to_fixed_point(notch_sos, "notch")

# -----------------------------------------------------------------------
# 4. RE-CHECK STABILITY AFTER QUANTIZATION
# -----------------------------------------------------------------------
# This is the step people skip. Rounding coefficients can nudge a pole
# just outside the unit circle even if the floating-point design was fine.


def check_fixed_stability(fixed_sections, name):
    print(f"\nPost-quantization stability check: {name}")
    for b_fixed, a_fixed in fixed_sections:
        a_float_again = a_fixed / SCALE
        poles = np.roots(a_float_again)
        mags = np.abs(poles)
        print(f"  requantized pole magnitudes: {mags}")
        if np.any(mags >= 1.0):
            print("  -> WARNING: quantization pushed a pole unstable. "
                  "Increase FRAC_BITS or redesign.")
        else:
            print("  -> still stable")


check_fixed_stability(hp_fixed, "high-pass")
check_fixed_stability(notch_fixed, "notch")

# -----------------------------------------------------------------------
# 5. PLOTS -- frequency response of the combined cascade
# -----------------------------------------------------------------------
combined_sos = np.vstack([hp_sos, notch_sos])
w, h = signal.sosfreqz(combined_sos, worN=2000, fs=FS)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))

ax1.plot(w, 20 * np.log10(np.maximum(np.abs(h), 1e-6)))
ax1.set_title('Combined high-pass + notch: magnitude response')
ax1.set_xlabel('Frequency (Hz)')
ax1.set_ylabel('Magnitude (dB)')
ax1.grid(True)
ax1.set_xlim(0, 125)

zeros, poles, _ = signal.sos2zpk(combined_sos)
theta = np.linspace(0, 2 * np.pi, 200)
ax2.plot(np.cos(theta), np.sin(theta), 'k--', linewidth=0.5)
ax2.scatter(poles.real, poles.imag, marker='x', s=80, label='poles')
ax2.scatter(zeros.real, zeros.imag, marker='o', s=80,
            facecolors='none', edgecolors='C1', label='zeros')
ax2.set_title('Pole-zero plot (must stay inside unit circle)')
ax2.set_xlabel('Real')
ax2.set_ylabel('Imaginary')
ax2.axis('equal')
ax2.legend()
ax2.grid(True)

plt.tight_layout()
plt.savefig('ecg_filter_response.png', dpi=150)
print("\nSaved plot to ecg_filter_response.png")
