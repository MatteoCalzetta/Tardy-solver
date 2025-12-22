# ==========================================================
#  MODELLO AMPL - RILASSAMENTO LINEARE
#         1 | r_j | sum U_j
# ==========================================================

set JOBS;

param H;

param r {JOBS};
param p {JOBS};
param d {JOBS};

# --------------------
# Variabili (RILASSATE)
# --------------------

# x[j,t] = frazione di job j che termina al tempo t
var x {J in JOBS, t in 0..H} >= 0 <= 1;

# completion time
var C {J in JOBS} >= 0;

# tardiness (rilassata)
var U {J in JOBS} >= 0 <= 1;

# --------------------
# Vincoli
# --------------------

s.t. OneCompletion {J in JOBS}:
    sum {t in 0..H} x[J,t] = 1;

s.t. CompletionDefinition {J in JOBS}:
    C[J] = sum {t in 0..H} t * x[J,t];

s.t. ReleaseDate {J in JOBS, t in 0..H: t < r[J] + p[J]}:
    x[J,t] = 0;

s.t. MachineCapacity {t in 0..H}:
    sum {J in JOBS, tau in max(0, t - p[J] + 1) .. t} x[J, tau] <= 1;

s.t. Tardiness {J in JOBS}:
    C[J] <= d[J] + H * U[J];

# --------------------
# Obiettivo
# --------------------
minimize TotalTardy:
    sum {J in JOBS} U[J];
