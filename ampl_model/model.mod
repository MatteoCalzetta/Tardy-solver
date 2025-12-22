# ==========================================================
#  MODELLO AMPL:
#         1 | r_j | sum U_j
# ==========================================================

# --------------------
# Insiemi e Parametri
# --------------------
set JOBS;

param n := card(JOBS);
param H;                  # upper bound (for example: max r_j + sum p_j)

param r {JOBS};           # release times
param p {JOBS};           # processing times
param d {JOBS};           # due dates


# --------------------
# Variabili
# --------------------

# x[j,t] = 1 se il job j termina esattamente al tempo t
var x {J in JOBS, t in 0..H} binary;

# Completion time di ciascun job
var C {J in JOBS} >= 0;

# Variabile tardività
var U {J in JOBS} binary;


# --------------------
# Vincoli
# --------------------

# (1) Ogni job deve terminare esattamente una volta
s.t. OneCompletion {J in JOBS}:
    sum {t in 0..H} x[J,t] = 1;


# (2) Definizione del completion time
s.t. CompletionDefinition {J in JOBS}:
    C[J] = sum {t in 0..H} t * x[J,t];


# (3) Release dates: non si può terminare prima di r_j + p_j
s.t. ReleaseDate {J in JOBS, t in 0..H: t < r[J] + p[J]}:
    x[J,t] = 0;


# (4) Capacità della macchina:
#     in ogni istante t può esserci *al massimo un job in lavorazione*
#
#     Un job che finisce a time = τ occupa la macchina nei tempi:
#         [τ - p[j], ..., τ - 1]
#
#     Per ogni time-slot t controlliamo tutti i job che potrebbero
#     ancora essere in lavorazione in quell'intervallo.
#
s.t. MachineCapacity {t in 0..H}:
    sum {J in JOBS, tau in max(0, t - p[J] + 1) .. t} x[J, tau]  <= 1;


# (5) Vincolo di tardività:
#     C_j > d_j  →  U_j = 1
#     C_j <= d_j →  U_j può essere 0
#
#     Implementato con Big-M (H va bene come M)
#
s.t. Tardiness {J in JOBS}:
    C[J] <= d[J] + H * U[J];


# --------------------
# Obiettivo
# --------------------
minimize TotalTardy:
    sum {J in JOBS} U[J];
