# fir_core.py
#
# MicroPython-friendly software model of the recovered Challenge 3 baseline
# FIR audio filter, shared by every Trojan model in this folder.
#
# Recovered filter (from bitstream reverse-engineering, Phase 2/3):
#   * 63-tap, linear-phase, low-pass FIR
#   * Q1.15 fixed-point coefficients, symmetric, DC gain = 1.0 (sum = 32768)
#   * -3 dB edge ~3296 Hz
#   * y[n] = sat16( (sum_k h[k]*x[n-k] + 2^14) >> 15 ), zero history
#
# Runs unchanged on CPython 3 and on MicroPython (rp2 / esp32 / unix ports).
# No csv/argparse/numpy are used so it loads on a bare microcontroller.

# --- Recovered Q1.15 coefficients (coeffs_q15, N=63, symmetric) --------------
COEFFS = [
    -14, 20, 27, -12, -45, -9, 63, 49, -66, -109, 34, 176, 49, -219, -187,
    198, 362, -71, -524, -188, 600, 577, -497, -1062, 104, 1575, 752, -2030,
    -2587, 2344, 10114, 13920, 10114, 2344, -2587, -2030, 752, 1575, 104,
    -1062, -497, 577, 600, -188, -524, -71, 362, 198, -187, -219, 49, 176,
    34, -109, -66, 49, 63, -9, -45, -12, 27, 20, -14,
]

N_TAPS = len(COEFFS)          # 63
Q15_HALF = 1 << 14            # rounding constant (2^14)
INT16_MIN = -(1 << 15)        # -32768
INT16_MAX = (1 << 15) - 1     #  32767
LATENCY = 2                   # verified end-to-end pipeline latency (frames)


def sat16(v):
    """Saturate an integer to the signed 16-bit range."""
    if v > INT16_MAX:
        return INT16_MAX
    if v < INT16_MIN:
        return INT16_MIN
    return v


class FIR:
    """Streaming direct-form FIR with a ring buffer and zero start history.

    step(x) feeds one int16 input sample and returns one int16 output sample,
    bit-identical to the golden reference fir() below.
    """

    def __init__(self, coeffs=None):
        self.h = list(coeffs) if coeffs is not None else list(COEFFS)
        self.n = len(self.h)
        self.buf = [0] * self.n   # buf[pos] = newest sample x[n]
        self.pos = 0

    def reset(self):
        for i in range(self.n):
            self.buf[i] = 0
        self.pos = 0

    def set_coeffs(self, coeffs):
        """Swap the coefficient set in place (history is preserved)."""
        self.h = list(coeffs)

    def step(self, x):
        buf = self.buf
        h = self.h
        n = self.n
        buf[self.pos] = x
        acc = 0
        p = self.pos
        for k in range(n):
            acc += h[k] * buf[p]
            p -= 1
            if p < 0:
                p = n - 1
        self.pos += 1
        if self.pos == n:
            self.pos = 0
        return sat16((acc + Q15_HALF) >> 15)


def fir(samples, coeffs=None):
    """Batch golden reference (zero history). Matches run_reference.py exactly."""
    h = list(coeffs) if coeffs is not None else list(COEFFS)
    n = len(h)
    y = [0] * len(samples)
    for i in range(len(samples)):
        acc = 0
        kmax = i + 1 if i + 1 < n else n
        for k in range(kmax):
            acc += h[k] * samples[i - k]
        y[i] = sat16((acc + Q15_HALF) >> 15)
    return y


def frame_output(left_logical, right_logical, latency=LATENCY):
    """Apply the pipeline framing shared by every reference model.

    Output frame m carries (left[m-latency], right[m-latency]); frames with a
    negative source index are power-up zeros. Returns a list of (left, right)
    int16 tuples, one per input frame.
    """
    m = len(left_logical)
    out = []
    for frame in range(m):
        s = frame - latency
        if 0 <= s < m:
            out.append((left_logical[s], right_logical[s]))
        else:
            out.append((0, 0))
    return out
