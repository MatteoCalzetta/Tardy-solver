# lower_bound/lower_bound.py

import heapq
from typing import List

import sys
import os

# Aggiusta il path se usi un package diverso
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from branch_and_bound.job import Job


# ===========================
# 1) LOWER BOUND KNAPSACK
# ===========================

def compute_lb_knapsack(jobs: List[Job]) -> int:
    """
    Lower bound via 'zaino' sul numero di job tardy.
    Idea:
      - prendo H = max d_j
      - considero un problema di knapsack 0-1:
            peso = p_j, valore = 1, capacità = H
      - K_star = massimo numero di job che riesco a 'mettere' in H
      - LB = n - K_star = minimo numero di tardy nel rilassamento

    Questo È un vero lower bound (rilassamento: tutti i job disponibili da 0,
    unica scadenza globale H).
    """
    n = len(jobs)
    if n == 0:
        return 0

    H = max(job.d for job in jobs)  # orizzonte massimo

    # dp[c] = massimo numero di job on-time con capacità c
    dp = [0] * (H + 1)

    for job in jobs:
        w = job.p
        # iterate backwards to avoid re-using the same job
        for c in range(H, w - 1, -1):
            dp[c] = max(dp[c], dp[c - w] + 1)

    K_star = max(dp)
    return n - K_star


# ===========================
# 2) EDF PREEMPTIVE - UTILITY
# ===========================

def simulate_pedd_tardy_count(jobs: List[Job]) -> int:
    """
    Simula una schedula preemptive EDD (Earliest Due Date) e
    restituisce il numero di job tardy in QUELLA schedula.

    IMPORTANTE:
      - Questo NON è garantito essere l'ottimo del problema preemptive
        1 | pmtn, r_j | sum U_j (per quello serve l'algoritmo di Lawler).
      - Quindi NON deve essere usato come lower bound nel B&B.
      - Potete usarlo solo per analisi/esperimenti.

    Logica:
      - ordino i job per release time
      - tengo una min-heap sui job attivi, chiave = due date
      - simulo preemption sugli arrivi
    """
    if not jobs:
        return 0

    # 1) Sort jobs by release time
    jobs_by_release = sorted(jobs, key=lambda job: job.r)

    # 2) Min-heap per job attivi: [due_date, remaining_time, job_id]
    active_heap = []

    # 3) Inizializza tempo e indice
    t = jobs_by_release[0].r
    idx = 0
    tardy_count = 0

    # 4) Simulazione
    while idx < len(jobs_by_release) or active_heap:
        # 4a) Rilascia nuovi job
        while idx < len(jobs_by_release) and jobs_by_release[idx].r <= t:
            job = jobs_by_release[idx]
            heapq.heappush(active_heap, [job.d, job.p, job.id])
            idx += 1

        # 4b) Se non ho job attivi, salto al prossimo rilascio
        if not active_heap:
            t = jobs_by_release[idx].r
            continue

        # 4c) Eseguo il job con due date minima
        due_date, rem_time, job_id = heapq.heappop(active_heap)

        # 4d) Prossimo evento: completamento o prossimo rilascio
        next_release = jobs_by_release[idx].r if idx < len(jobs_by_release) else float('inf')
        run_time = min(rem_time, next_release - t)

        # 4e) Avanza il tempo
        t += run_time
        rem_time -= run_time

        # 4f) Completion check
        if rem_time == 0:
            if t > due_date:
                tardy_count += 1
        else:
            heapq.heappush(active_heap, [due_date, rem_time, job_id])

    return tardy_count
