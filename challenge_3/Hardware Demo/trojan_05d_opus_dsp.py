# trojan_05d_opus_dsp.py
#
# MicroPython model of Candidate 05D ("Opus DSP").
#
# Trigger : a Goertzel single-bin tone detector at fs/3 (~5333 Hz; bin k=192 in
#           a 576-sample window). At that bin the Goertzel coefficient is -1, so
#           the recurrence is add/subtract only:  s0 = x - s1 - s2.
#           At the end of each non-overlapping 576-sample window, the L1
#           magnitude |s1| + |s2| is compared to ARM_THRESHOLD = 2^23. Meeting
#           it sets a STICKY arm latch that never clears.
# Payload : while armed, odd-index coefficients are negated (h'[k] = (-1)^k h[k]),
#           turning the low-pass FIR into a high-pass (spectral inversion). The
#           datapath is otherwise unchanged -- this is NOT a bypass.
# Timing  : the latch set at a window boundary affects only later samples; for a
#           full-scale fs/3 tone the first armed sample is n = 576. Right channel
#           echoes the raw input; latency 2.
#
# Reconstructed from the Phase 5 reference ref_trojan.py in the CSAW
# documentation repo (05D is not shipped in this local quality-winner copy).

from fir_core import COEFFS, N_TAPS, Q15_HALF, sat16, frame_output, LATENCY

WINDOW = 576
ARM_THRESHOLD = 1 << 23
FS = 16000                 # nominal sample rate; trigger tone = FS / 3


class OpusDspTrojan:
    def __init__(self):
        self.h = list(COEFFS)
        # spectral-inversion set: negate odd-index taps
        self.h_inv = [(-c if (k & 1) else c) for k, c in enumerate(self.h)]
        self.buf = [0] * N_TAPS
        self.pos = 0
        self.s1 = 0
        self.s2 = 0
        self.wcount = 0
        self.armed = False
        self.armed_sample = None
        self.samples_armed = 0
        self.i = -1

    def reset(self):
        for i in range(N_TAPS):
            self.buf[i] = 0
        self.pos = 0
        self.s1 = 0
        self.s2 = 0
        self.wcount = 0
        self.armed = False
        self.armed_sample = None
        self.samples_armed = 0
        self.i = -1

    def step(self, x):
        self.i += 1

        # FIR uses the latch value captured BEFORE this sample's Goertzel update.
        coeffs = self.h_inv if self.armed else self.h
        self.buf[self.pos] = x
        acc = 0
        p = self.pos
        for k in range(N_TAPS):
            acc += coeffs[k] * self.buf[p]
            p -= 1
            if p < 0:
                p = N_TAPS - 1
        self.pos += 1
        if self.pos == N_TAPS:
            self.pos = 0
        y = sat16((acc + Q15_HALF) >> 15)
        if self.armed:
            self.samples_armed += 1

        # Goertzel update at bin fs/3 (coefficient = -1): s0 = x - s1 - s2
        s0 = x - self.s1 - self.s2
        self.s2 = self.s1
        self.s1 = s0
        self.wcount += 1
        if self.wcount == WINDOW:
            mag = abs(self.s1) + abs(self.s2)
            if not self.armed and mag >= ARM_THRESHOLD:
                self.armed = True
                self.armed_sample = self.i + 1   # affects the next sample
            self.s1 = 0
            self.s2 = 0
            self.wcount = 0

        return y

    def run(self, samples, latency=LATENCY):
        self.reset()
        left_logical = [self.step(x) for x in samples]
        right_logical = list(samples)
        frames = frame_output(left_logical, right_logical, latency)
        stats = {
            "frames": len(samples),
            "armed": self.armed,
            "armed_sample": self.armed_sample,
            "samples_armed": self.samples_armed,
            "payload": "spectral_inversion_highpass",
            "latency_frames": latency,
        }
        return frames, stats


def _demo():
    import math
    # One full-scale fs/3 tone -> arms at the first 576-sample boundary.
    n = WINDOW * 3
    tone = [int(32000 * math.cos(2.0 * math.pi * (FS / 3) * i / FS)) for i in range(n)]
    t = OpusDspTrojan()
    _, stats = t.run(tone)
    print("05D Opus DSP:", stats)


if __name__ == "__main__":
    _demo()
