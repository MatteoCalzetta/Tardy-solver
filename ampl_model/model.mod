# Variabili 
	param n integer >0; # jobs 
set JOBS := 1..n;
param r {JOBS} >= 0; # release date
param p {JOBS} >= 0; # durata del job 
param d {JOBS} >= 0; # due date 

#param H = max {j in JOBS}(r[j]+ p[j]); # upper bound al tempo di completameto
param H >= 0; # upper bound al tempo di completamento, lo settiamo da Python

var x {j in JOBS, t in 0..H} binary;


#var x {JOBS, 0..H} binary; # time‐indexed: x[j,t]=1 se job j finisce al tempo t

var U {j in JOBS} binary;  # U[j]=1 se j è tardy 


# Vincoli 
# ciascun job finisce esattamente una volta:
CompleteOnce {j in JOBS}:
    sum {t in 0..H} x[j,t] = 1;
    
# precedenze r_j: nessun x[j,t] con t < r[j]+p[j]
ReleaseTime {j in JOBS, t in 0..H: t < r[j] + p[j]}:
    x[j,t] = 0;
    
# definizione tardy:
TardyDef {j in JOBS}:
    sum {t in 0..d[j]} x[j,t] + U[j] = 1;

# Funzione Obiettivo
minimize TotalTardy: sum {j in JOBS} U[j];

