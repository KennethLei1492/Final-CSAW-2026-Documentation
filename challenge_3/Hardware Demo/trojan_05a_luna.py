# trojan_05a_luna.py
#
# MicroPython model of Candidate 05A ("Luna").
#
# Trigger : a 3-sample knock on the LEFT channel, each value masked to 16 bits.
#           pattern = (0x5A3C, 0xC3A5, 0x96E1)
# Payload : from the trigger sample onward (permanent), the filtered left
#           output has its least-significant bit flipped (y ^ 1). Right channel
#           echoes the raw input. No bypass window -- the corruption is sticky.
#
# Reconstructed from the Phase 5 reference run_candidate_reference.py in the
# CSAW documentation repo (05A is not shipped in this local quality-winner copy).

from fir_core import FIR, frame_output, LATENCY

TRIGGER = (0x5A3C, 0xC3A5, 0x96E1)


class LunaTrojan:
    def __init__(self):
        self.fir = FIR()
        self.win = []          # last up to 3 masked left samples
        self.armed = False
        self.armed_index = None
        self.i = -1

    def reset(self):
        self.fir.reset()
        self.win = []
        self.armed = False
        self.armed_index = None
        self.i = -1

    def step(self, x):
        """Feed one int16 input sample, return the logical left output sample."""
        self.i += 1
        y = self.fir.step(x)

        m = x & 0xFFFF
        self.win.append(m)
        if len(self.win) > 3:
            self.win.pop(0)
        if not self.armed and len(self.win) == 3 and tuple(self.win) == TRIGGER:
            self.armed = True
            self.armed_index = self.i

        return (y ^ 1) if self.armed else y

    def run(self, samples, latency=LATENCY):
        """Return (frames, stats). frames is a list of (left, right) int16 tuples."""
        self.reset()
        left_logical = [self.step(x) for x in samples]
        right_logical = list(samples)
        frames = frame_output(left_logical, right_logical, latency)
        stats = {
            "frames": len(samples),
            "trigger_index": self.armed_index,
            "triggered": self.armed,
            "payload": "lsb_flip",
            "latency_frames": latency,
        }
        return frames, stats


def _demo():
    # 20 quiet samples, the knock, then 10 more -> everything after flips LSB.
    samples = [100] * 20 + [0x5A3C, 0xC3A5, 0x96E1] + [100] * 10
    t = LunaTrojan()
    _, stats = t.run(samples)
    print("05A Luna:", stats)


if __name__ == "__main__":
    _demo()
