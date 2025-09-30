# ---------------- VARIABILI ----------------
param n integer >0;   # numero di job
param H >= 0;         # upper bound completamento
set JOBS := 1..n;

param r {JOBS} >= 0;  # release date
param p {JOBS} >= 0;  # durata del job
param d {JOBS} >= 0;  # due date

var x {j in JOBS, t in 0..H} binary;  # x[j,t]=1 se job j finisce al tempo t
var U {j in JOBS} binary;              # U[j]=1 se job j è tardy

# ---------------- VINCOLI ----------------

# ciascun job finisce esattamente una volta
s.t. CompleteOnce {j in JOBS}:
    sum {t in 0..H} x[j,t] = 1;

# release date: job non può finire prima di r[j]+p[j]
s.t. ReleaseTime {j in JOBS, t in 0..H: t < r[j]+p[j]}:
    x[j,t] = 0;

# vincolo di capacità: un solo job per volta
s.t. Capacity {h in 0..H}:
    sum {j in JOBS, t in 0..H: t-p[j] < h && h <= t} x[j,t] <= 1;

# definizione tardy: U[j]=1 se job finisce oltre la due date
s.t. TardyDef {j in JOBS}:
    U[j] >= sum {t in d[j]+1..H} x[j,t];

# ---------------- FUNZIONE OBIETTIVO ----------------
minimize TotalTardy: sum {j in JOBS} U[j];
