# 02. Independent arithmetic recheck

## Parameter / storage / F-MAC comparison

All values below were independently reconstructed from the B2/LR2/H2 shapes. `Free slow` excludes frozen-zero coordinates `318*(d+1)`. INT8 sizes are derived using ASTRA's declared packing policy; LR2/H2 sizes are not yet official manifests.

| d | Family | Tensors | Allocated | Free slow | FP16 MiB | Packed INT8 MiB | F MAC/step |
|---:|---|---:|---:|---:|---:|---:|---:|
|512|B2|118|23 015 887|22 852 753|43.899321|22.268860|4 456 448|
|512|LR2-r64|150|20 394 447|20 231 313|38.899321|19.780579|1 835 008|
|512|H2|122|24 064 463|23 901 329|45.899321|23.277161|4 456 448|
|1024|B2|198|55 451 639|55 125 689|105.765608|53.285583|17 301 504|
|1024|LR2-r64|262|43 917 303|43 591 353|83.765608|42.309021|5 767 168|
|1024|H2|202|59 645 943|59 319 993|113.765608|57.301697|17 301 504|
|1536|B2|278|97 340 959|96 852 193|185.663145|93.318054|38 535 168|
|1536|LR2-r64|374|70 602 271|70 113 505|134.663145|67.853210|11 796 480|
|1536|H2|282|106 778 143|106 289 377|203.663145|102.341980|38 535 168|
|2048|B2|358|148 683 847|148 032 265|283.591932|142.366028|68 157 440|
|2048|LR2-r64|486|100 449 351|99 797 769|191.591932|96.412903|19 922 944|
|2048|H2|362|165 461 063|164 809 481|315.591932|158.397766|68 157 440|

### d=1024 exact corrections

- B1/W1 from V2.2: 55 320 439 parameters and 196 tensors.
- B2: 55 451 639 parameters and 198 tensors.
- Difference: `131 200 = 128*(1024+1)`, exactly `W_R[128,1024] + b_R[128]`.
- `W_R` rows 3–23 are trainable; other rows are frozen-zero. `P` has 128×1024 allocated slots, 21×1024=21 504 active fast coordinates.
- Fixed-zero slow coordinates: `318*(1024+1)=325 950`; free slow coordinates: 55 125 689.
- B2 packed INT8 ABI: 55 873 984 bytes (53.285583 MiB). The former `e_tau` ambiguity is resolved by storing `e_modality` as FP32 vector class and `W_wake` as INT8 row matrix.
- LR2 is not the V2.2 old count: B2 adds the same 131 200 `W_R` parameters, so LR2 is 43 917 303, not 43 786 103.
- H2 adds four d×d attention matrices to B2; at d=1024 this adds 4 194 304 parameters and 8 MiB raw FP16. Its FP16 K/V cache for Nctx=256 is `4*Nctx*d = 1 048 576 bytes` (1 MiB).

## d=1024 compute paths

- Full B2 F: 17 301 504 MAC/step.
- ASR, 100 frames/s, K=8, all 16 blocks: 14 210 672 000 MAC/s before DSP/controller overhead.
- ASR, 100 frames/s, K=1, q=4/16 blocks: 801 289 600 MAC/s.
- TTS, 1000 frames, K=8: 142 239 840 000 MAC.
- Image, 256 RGB 16×16 patches, K=8: 36 526 120 960 MAC.
- Text generation, 128 output tokens, full K=8 event cost: 22 457 364 480 MAC.
- LR2-r64: F=5 767 168 MAC/step; ASR full K8 100fps=4 983 203 200 MAC/s; 128-token text event total=10 646 204 416 MAC.
- H2 adds `4*d² + 2*Nctx*d = 4 718 592 MAC/event` at d=1024,Nctx=256, before any quality benefit is established.

The V2.2 value 22 011 707 392 MAC for 128 tokens is still a valid lower-bound subtotal for `128*(8*F_MAC + V*d)` only. It omits per-token encoder, full memory scan, selector and wake overhead. It must not be presented as the full event path.

## Memory / training arithmetic

- B2 FP16 weights: 110 903 278 bytes =105.765608 MiB.
- Fast P allocation: 4*128*1024=524 288 bytes=0.5 MiB.
- Explicit FP16 live-allocation subtotal from ASTRA: 160 930 866 bytes=153.475633621 MiB, before named capture/backend/controller/driver/snapshot extras. This is not total PSS.
- B4,L256,K8,d1024 activation allocation formula gives 542 113 792 bytes≈517 MiB. With 18P≈951.89 MiB, the stated subtotal is ≈1468.89 MiB before backend buffers and other extras. This is a training scenario, not an A52 runtime measurement.

## LR2 is not equivalent to B2

The V2.2 span-129 counterexample remains valid for B2/LR2: a dense branch can produce 129 linearly independent input-gradient directions, while two rank-64 A factors constrain all gradients to a fixed subspace of dimension at most 128. This refutes exact W1/B2-to-LR2 equivalence; it does not predict measured task-quality loss. No architecture is selected by parameter/MAC savings alone.
