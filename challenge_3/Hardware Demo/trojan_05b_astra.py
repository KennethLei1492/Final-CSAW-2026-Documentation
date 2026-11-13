# trojan_05b_astra.py
#
# MicroPython model of Candidate 05B ("Astra") -- the SELECTED candidate.
#
# Trigger : 8 consecutive LEFT-channel samples equal to the magic sequence.
#           MAGIC = (32512, -32511, 23100, -23101, 28050, -28051, -15556, 15555)
# Payload : on completion, bypass the FIR for 128 frames (raw left audio passes
#           straight through); then the filter resumes. Re-triggerable. The
#           expiry sample sits outside the payload and may begin a new match.
# Framing : left = raw when active else filtered; right = raw echo; latency 2.
#
# Ported bit-for-bit from the local Phase 5 reference
#   experiments/phase05/05b-astra/tests/candidate_reference.py

from fir_core import FIR, frame_output, LATENCY

MAGIC = (32512, -32511, 23100, -23101, 28050, -28051, -15556, 15555)
BYPASS_FRAMES = 128


class AstraTrojan:
    def __init__(self):
        self.fir = FIR()
        self.pos = 0
        self.active = False
        self.remaining = 0
        self.hits = []
        self.active_count = 0
        self.i = -1

    def reset(self):
        self.fir.reset()
        self.pos = 0
        self.active = False
        self.remaining = 0
        self.hits = []
        self.active_count = 0
        self.i = -1

    def step(self, x):
        """Feed one int16 input sample, return the logical left output sample.

        The FSM update below mirrors the reference exactly; the output uses the
        'active' state AFTER the update (reference's active_after[n]).
        """
        self.i += 1
        y = self.fir.step(x)

        if self.active:
            self.pos = 0
            if self.remaining <= 1:
                self.remaining = 0
                self.active = False
                # expiry sample is outside the payload and can start a match
                self.pos = 1 if x == MAGIC[0] else 0
            else:
                self.remaining -= 1
        elif x == MAGIC[self.pos]:
            if self.pos == len(MAGIC) - 1:
                self.pos = 0
                self.remaining = BYPASS_FRAMES
                self.active = True
                self.hits.append(self.i)
            else:
                self.pos += 1
        elif x == MAGIC[0]:
            self.pos = 1
        else:
            self.pos = 0

        if self.active:
            self.active_count += 1
            return x        # bypass: raw audio
        return y            # filtered

    def run(self, samples, latency=LATENCY):
        self.reset()
        left_logical = [self.step(x) for x in samples]
        right_logical = list(samples)
        frames = frame_output(left_logical, right_logical, latency)
        stats = {
            "frames": len(samples),
            "trigger_completions": list(self.hits),
            "trigger_events": len(self.hits),
            "active_frames": self.active_count,
            "bypass_frames_per_trigger": BYPASS_FRAMES,
            "payload": "fir_bypass",
            "latency_frames": latency,
        }
        return frames, stats


def _demo():
    samples = [0] * 10 + list(MAGIC) + [777] * 200
    t = AstraTrojan()
    _, stats = t.run(samples)
    print("05B Astra:", stats)


if __name__ == "__main__":
    _demo()
