# trojan_05c_opus_arch.py
#
# MicroPython model of Candidate 05C ("Opus Architecture").
#
# Trigger : an ordered 3-frame "knock" on the RIGHT I2S slot, each value masked
#           to 16 bits. MAGIC = (0xC0DE, 0xFACE, 0xBEEF), tracked by a 3-state
#           FSM with restart credit on 0xC0DE; the arm latch is sticky.
# Payload : once armed (permanent), the left output is the raw LEFT input sample
#           instead of the FIR result. The right output echoes the raw LEFT
#           input. Framing: bypass for every frame at/after the armed frame;
#           latency 2.
#
# IMPORTANT: unlike 05A/05B (which trigger on the left channel), 05C watches the
# RIGHT input slot, which the harness drives INDEPENDENTLY of the left audio --
# the knock can be delivered on the right channel without disturbing the left.
# So this model takes a separate right sample. In the real deployed system the
# I2S bridge mirrors L = R on input, so if you pass only a left sample the right
# defaults to it (right = left).
#
# Ported bit-for-bit from the Phase 5 reference
#   experiments/phase05/05c-opus-architecture/tests/trojan_ref.py  (arm_index).

from fir_core import FIR, frame_output, LATENCY

MAGIC = (0xC0DE, 0xFACE, 0xBEEF)


def to_s16(u):
    """Interpret an unsigned 16-bit word as a signed int16 (helper for demos)."""
    u &= 0xFFFF
    return u - 0x10000 if u & 0x8000 else u


class OpusArchTrojan:
    def __init__(self):
        self.fir = FIR()
        self.state = 0            # seq_idx in the reference detector
        self.armed = False
        self.armed_index = None
        self.i = -1

    def reset(self):
        self.fir.reset()
        self.state = 0
        self.armed = False
        self.armed_index = None
        self.i = -1

    def step(self, left, right=None):
        """Feed one frame; return the logical left output sample.

        `left`  is the audio sample to filter.
        `right` is the RIGHT I2S slot carrying the knock; if omitted it mirrors
                `left` (the real-system L = R input case).
        """
        self.i += 1
        y = self.fir.step(left)

        rv = (left if right is None else right) & 0xFFFF
        if not self.armed:
            if self.state == 0:
                self.state = 1 if rv == MAGIC[0] else 0
            elif self.state == 1:
                if rv == MAGIC[1]:
                    self.state = 2
                elif rv == MAGIC[0]:
                    self.state = 1
                else:
                    self.state = 0
            elif self.state == 2:
                if rv == MAGIC[2]:
                    self.armed = True          # sticky; effective at this frame
                    self.armed_index = self.i
                elif rv == MAGIC[0]:
                    self.state = 1
                else:
                    self.state = 0

        return left if self.armed else y

    def run(self, frames_in, latency=LATENCY):
        """frames_in is a list of left ints (right mirrors left) OR of
        (left, right) pairs. Returns (frames, stats)."""
        self.reset()
        left_logical = []
        right_echo = []
        for item in frames_in:
            if isinstance(item, (tuple, list)):
                left, right = item[0], item[1]
            else:
                left, right = item, None
            left_logical.append(self.step(left, right))
            right_echo.append(left)            # right OUTPUT echoes raw left input
        frames = frame_output(left_logical, right_echo, latency)
        armed_frames = 0
        if self.armed_index is not None:
            armed_frames = len(frames_in) - self.armed_index
        stats = {
            "frames": len(frames_in),
            "armed_index": self.armed_index,
            "armed": self.armed,
            "armed_frames": armed_frames,
            "payload": "fir_bypass_sticky",
            "trigger_channel": "right",
            "latency_frames": latency,
        }
        return frames, stats


def _demo():
    knock = [to_s16(v) for v in MAGIC]
    # Benign left audio throughout; the knock rides ONLY on the right channel.
    frames_in = ([(50, 50)] * 15
                 + [(50, knock[0]), (50, knock[1]), (50, knock[2])]
                 + [(50, 50)] * 20)
    t = OpusArchTrojan()
    _, stats = t.run(frames_in)
    print("05C Opus Architecture:", stats)


if __name__ == "__main__":
    _demo()
