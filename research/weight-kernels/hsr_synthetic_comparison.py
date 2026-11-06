import numpy as np
# Reproducible structural approximation only; no trained neural task.
n, rank, corrections = 256, 32, 4
rng = np.random.default_rng(20261106)
a = rng.normal(0, .08, (n, rank))
b = rng.normal(0, .08, (rank, n))
target = a @ b
for i in range(n):
    cols = rng.choice(n, corrections, replace=False)
    target[i, cols] += rng.normal(0, .4, corrections)
u, s, vh = np.linalg.svd(target, full_matrices=False)
lowrank = (u[:, :rank] * s[:rank]) @ vh[:rank, :]
residual = target - lowrank
idx = np.argpartition(np.abs(residual), -corrections, axis=1)[:, -corrections:]
sparse = np.zeros_like(residual)
np.put_along_axis(sparse, idx, np.take_along_axis(residual, idx, axis=1), axis=1)
x = rng.normal(size=(512, n))
for name, approx, params in [
    ("dense", target, n*n),
    ("rank32", lowrank, 2*n*rank),
    ("HSR-rank32-sparse4", lowrank+sparse, 2*n*rank+n*corrections),
]:
    error = np.linalg.norm((target-approx) @ x.T)/np.linalg.norm(target @ x.T)
    print(name, "params", params, "relative_output_error", round(float(error), 6))
