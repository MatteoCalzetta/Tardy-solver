# lower_bound/lower_bound.py
#
# Lower bounds per 1|r_j|sum U_j ispirati al modello preemptive di Lawler (1990).
# Usiamo:
#   (1) un LB da "overload di intervallo" (condizione di Horn/Lawler),
#   (2) un LB knapsack grezzo sull'orizzonte H = max d_j,
# e prendiamo il massimo tra i due.

from typing import List
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from branch_and_bound.job import Job


# ------------------------------------------------------------
# 1) LB "zaino" — corretto ma conservativo
# ------------------------------------------------------------
def compute_lb_knapsack(jobs: List[Job]) -> int:
    """
    Lower bound via 'zaino' sul numero di job tardy.
    Idea: nell'orizzonte H = max d_j posso allocare al più K_star job on-time,
    dove ogni job "costa" p_j e "vale" 1.
    LB = n - K_star.

    NOTA: ignora release date e struttura fine del calendario, quindi è conservativo
          (ma sempre un bound valido).
    """
    n = len(jobs)
    if n == 0:
        return 0

    H = max(job.d for job in jobs)  # orizzonte massimo (grezzo)
    if H <= 0:
        return 0

    # dp[c] = massimo numero di job on-time schedulabili con capacità c
    dp = [0] * (H + 1)
    for job in jobs:
        w = max(0, int(job.p))  # uso p_j arrotondato per difetto
        if w <= 0 or w > H:
            continue
        # knapsack 0/1 classico: ciclo a ritroso sulla capacità
        for c in range(H, w - 1, -1):
            dp[c] = max(dp[c], dp[c - w] + 1)

    K_star = max(dp)
    lb = n - K_star
    return max(0, lb)


# ------------------------------------------------------------
# 2) LB "overload di intervallo" (Horn / Lawler) — VALIDO
# ------------------------------------------------------------
def compute_lb_overload_intervals(jobs: List[Job]) -> int:
    """
    Lower bound basato sulla condizione di fattibilità per 1|pmtn,r_j|:

      per ogni intervallo [a,b], la domanda
          D([a,b]) = sum_{j: r_j >= a, d_j <= b} p_j
      deve soddisfare D([a,b]) <= b - a in qualsiasi schedula che tenga tutti
      questi job on-time.

    Se per qualche [a,b] si ha D([a,b]) > b - a, esiste un overload.
    Ogni job "rimosso" può liberare al più p_max, quindi:

        LB_over >= ceil( max_{[a,b]} (D([a,b]) - (b-a)) / p_max ).

    Questo LB è sempre valido (deriva dal modello preemptive di Lawler),
    ma può essere conservativo.
    """
    n = len(jobs)
    if n == 0:
        return 0

    # Punti candidati: tutte le r_j e d_j
    pts = sorted({float(j.r) for j in jobs} | {float(j.d) for j in jobs})
    if len(pts) < 2:
        return 0

    pmax = max((float(j.p) for j in jobs), default=0.0)
    if pmax <= 0:
        return 0

    worst_overload = 0.0

    # Esamina tutti gli intervalli [a,b] definiti dai punti candidati
    for i, a in enumerate(pts):
        for b in pts[i+1:]:
            if b <= a:
                continue
            # domanda D([a,b]) = somma dei p_j dei job completamente contenuti
            demand = 0.0
            for j in jobs:
                if j.r >= a and j.d <= b:
                    demand += float(j.p)
            capacity = b - a
            overload = demand - capacity
            if overload > worst_overload:
                worst_overload = overload

    if worst_overload <= 0:
        return 0

    # Traduci overload di tempo in #job minimi da rendere tardy
    # ceil(worst_overload / pmax) con piccolo aggiustamento numerico
    lb_jobs = int((worst_overload + pmax - 1e-9) // pmax)
    lb_jobs = max(0, lb_jobs)
    return min(n, lb_jobs)


# ------------------------------------------------------------
# 3) LB COMBINATO: max(overload, knapsack)
# ------------------------------------------------------------
def compute_lb_combined(jobs: List[Job]) -> int:
    """
    Restituisce un LB valido sul numero di job tardy tra 'jobs', ottenuto come:

        LB = max( LB_overload_intervals, LB_knapsack )

    Entrambe le componenti sono lower bound corretti per il modello preemptive
    (Lawler/Horn); nel B&B li usiamo su F = job "ancora liberi" come rilassamento
    del problema originale.
    """
    if not jobs:
        return 0

    lb_over = compute_lb_overload_intervals(jobs)
    lb_kp = compute_lb_knapsack(jobs)

    lb = max(lb_over, lb_kp)
    n = len(jobs)
    if lb < 0:
        lb = 0
    if lb > n:
        lb = n
    return lb
