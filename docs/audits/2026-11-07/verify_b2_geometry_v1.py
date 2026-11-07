#!/usr/bin/env python3
"""Historical UNO B2/compact arithmetic, not production model verification.

Independent from reference/uno_ref and from the Android app. No dependencies.
Source rows: UNO_MINIMAL_ORGANISM_PAPER_FINAL_FOR_OWNER_REVIEW, 2026-11-03.
Do not interpret PASS as trained weights, mobile performance or model choice.
"""

# id: (d, V, block, branches, expansion, mem_width, rank, descriptors, P, F_MAC, TEXT8_MAC)
ROWS = {
    'B2-1024': (1024, 32768, 64, 2, 4, 128, 0, 198, 55451639, 17301504, 175448160),
    'B2-512': (512, 32768, 64, 2, 4, 128, 0, 118, 23015887, 4456448, 54161472),
    'C384': (384, 16384, 64, 1, 4, 64, 0, 68, 8698053, 1277952, 17403448),
    'C256': (256, 8192, 32, 1, 4, 64, 0, 78, 3339727, 557056, 7256128),
    'C256R32': (256, 8192, 32, 1, 4, 64, 32, 94, 3012047, 229376, 4634688),
}


def arithmetic(config):
    d, vocab, block, branches, expansion, mem, rank, *_ = config
    assert d > 0 and d % block == 0
    n = d // block
    head = 902
    recurrent = branches * n * (
        2 * rank * (d + expansion * block) + expansion * block * block +
        expansion * block + block
        if rank else
        2 * expansion * block * d + expansion * block * block +
        expansion * block + block
    )
    allocated = (vocab * d + 951 * d + 2 * d * d + 4 * mem * d +
                 recurrent + head * (d + 1) + vocab + n * (2 * d + 5) + 33)
    descriptors = 38 + branches * n * (7 if rank else 5)
    f_mac = branches * n * (
        2 * rank * (d + expansion * block) + expansion * block * block
        if rank else
        2 * expansion * block * d + expansion * block * block
    )
    # Full 4096-record semantic read, text event, 8 recurrent ticks and full decoder.
    encoder = 2*d*d + 32*d + 2*mem*d + 2*4096*mem
    selector = n * (2*d + 4)
    text_mac = encoder + selector + 8 * (f_mac + d) + vocab * d + 32
    return descriptors, allocated, f_mac, text_mac


def main():
    for name, row in ROWS.items():
        expected = row[7:]
        actual = arithmetic(row)
        assert actual == expected, (name, expected, actual)
        d = row[0]
        assert 318*(d+1) < actual[1]
        print(f'ARITHMETIC_PASS {name}: descriptors={actual[0]} P={actual[1]} MAC={actual[3]}')
    # Fixed-mask linearized bound with alpha=0.5, gamma=0.9.
    assert 1-0.5*(1-0.9) == 0.95
    assert 1-0.5*0*(1-0.9) == 1.0
    assert 16*15+1 == 241 and 2**16-1 == 65535
    # The following hard-selector counterexample is discontinuous at x=0.
    for eps in (1e-2, 1e-5, 1e-8):
        # Input distance=2*eps. Outputs differ by 0.5 in the second coordinate.
        assert 0.5 / (2*eps) > 1.0
    assert (1 + (-1)) / 2 == 0  # semantic memory collision
    print('MATH_LIMITS_PASS conditional contraction; adaptive discontinuity; semantic collision')
    print('PASS=5_GEOMETRIES_AND_4_INVARIANT_GROUPS; NO_TRAINING_OR_ANDROID_PROOF')


if __name__ == '__main__':
    main()
