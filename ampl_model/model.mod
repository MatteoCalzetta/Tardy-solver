# ---------------- PARAMETRI ----------------
param n integer > 0;        # numero di job
param H >= 0;               # upper bound sull'orizzonte temporale
set JOBS := 1..n;

param r {JOBS} >= 0;        # release date di ciascun job
param p {JOBS} >= 0;        # processing time
param d {JOBS} >= 0;        # due date

# (opzionale) pesi per ∑ w_j U_j; se non servono, si può lasciare tutto a 1
param w {JOBS} >= 0 default 1;

# ---------------- VARIABILI ----------------

# x[j,t] = 1 se il job j termina esattamente al tempo t
var x {j in JOBS, t in 0..H} binary;

# U[j] = 1 se il job j è tardy (C_j > d_j)
var U {j in JOBS} binary;

# completion time C_j (intero per consistenza con t)
var C {j in JOBS} >= 0, integer;

# ---------------- VINCOLI ----------------

# (1) Ogni job deve terminare esattamente una volta
s.t. CompleteOnce {j in JOBS}:
    sum {t in 0..H} x[j,t] = 1;

# (2) Release date: il job non può terminare prima di r[j] + p[j]
s.t. ReleaseTime {j in JOBS, t in 0..H: t < r[j] + p[j]}:
    x[j,t] = 0;

# (3) Vincolo di capacità: in ogni istante h può girare al più un job
# Se il job j termina al tempo t, occupa l'intervallo (t - p[j], t]
s.t. Capacity {h in 1..H}:
    sum {j in JOBS, t in 0..H: t - p[j] < h && h <= t} x[j,t] <= 1;

# (4) Definizione del completion time C[j] come tempo di fine del job
s.t. Cdef {j in JOBS}:
    C[j] = sum {t in 0..H} t * x[j,t];

# (5) Definizione di tardività:
#     U[j] = 1 se e solo se C[j] > d[j], altrimenti 0.
#     Dato che il job termina una sola volta, la somma di x[j,t] per t>d[j]
#     è 1 se il job è tardy, 0 altrimenti.
s.t. TardyDef {j in JOBS}:
    U[j] = sum {t in d[j]+1..H} x[j,t];

# ---------------- FUNZIONE OBIETTIVO ----------------
# Se vuoi il caso non pesato:       w[j] = 1 per tutti j
# Se vuoi il caso pesato:           imposta w[j] adeguatamente nel .dat
minimize TotalTardy:
    sum {j in JOBS} w[j] * U[j];
