"""java.util.Random, 48-bit LCG. Used only so the holdout generator is deterministic."""

MASK = (1 << 48) - 1
MULT = 0x5DEECE66D
ADD = 0xB


def _i32(x):
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x >= 0x80000000 else x


class JavaRandom:
    def __init__(self, seed):
        self.seed = (int(seed) ^ MULT) & MASK

    def next(self, bits):
        self.seed = (self.seed * MULT + ADD) & MASK
        return self.seed >> (48 - bits)

    def next_double(self):
        return ((self.next(26) << 27) + self.next(27)) / float(1 << 53)

    def next_int(self, bound):
        if bound <= 0:
            raise ValueError("bound")
        if (bound & -bound) == bound:
            return (bound * self.next(31)) >> 31
        while True:
            bits = self.next(31)
            val = bits % bound
            if _i32(bits - val + (bound - 1)) >= 0:
                return val

    def shuffled(self, items):
        data = list(items)
        for i in range(len(data) - 1, 0, -1):
            j = self.next_int(i + 1)
            data[i], data[j] = data[j], data[i]
        return data
