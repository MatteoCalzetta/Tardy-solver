import heapq
from typing import List
import sys
import os
from lower_bound.ampl_interface import run_ampl_relax_node

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
    - considero un problema di knapsack 0-1: peso = p_j, valore = 1, capacità = H
    - K_star = massimo numero di job che riesco a 'mettere' in H
    - LB = n - K_star = minimo numero di tardy nel rilassamento

    Questo È un vero lower bound.
    """
    n = len(jobs)
    if n == 0:
        return 0

    H = max(job.d for job in jobs)  # orizzonte massimo

    # dp[c] = massimo numero di job on-time con capacità c
    dp = [0] * (H + 1)
    for job in jobs:
        w = job.p
        # itera a ritroso per evitare di riusare lo stesso job
        for c in range(H, w - 1, -1):
            dp[c] = max(dp[c], dp[c - w] + 1)

    K_star = max(dp)
    return n - K_star

# ===========================
# 2) LOWER BOUND MOORE
# ===========================
def compute_lb_moore(jobs: List[Job]) -> int:
    """
    Lower bound basato sull'algoritmo di Moore-Hodgson per 1 || sum U_j.

    Idea:
    - si "dimenticano" le release date vere e proprie
    - r_min = min r_j tra questi job
    - si immagina di poter iniziare a tempo r_min
    - d_eff_j = d_j - r_min
    - si applica l'algoritmo di Moore sulle due-date effettive
    """
    n = len(jobs)
    if n == 0:
        return 0

    # 1) Trova il minimo r_j
    r_min = min(job.r for job in jobs)

    # 2) Costruisci lista con due date "shiftate"
    jobs_eff = [(job.d - r_min, job.p, job.id) for job in jobs]

    # 3) Ordina per due date effettive crescenti
    jobs_eff.sort(key=lambda x: x[0])

    # 4) Algoritmo di Moore-Hodgson
    t = 0
    max_heap = []  # (-p_j, job_id)
    tardy_ids = set()

    for d_eff, p, job_id in jobs_eff:
        t += p
        heapq.heappush(max_heap, (-p, job_id))
        if t > d_eff:
            neg_p_max, jid_max = heapq.heappop(max_heap)
            p_max = -neg_p_max
            t -= p_max
            tardy_ids.add(jid_max)

    return len(tardy_ids)

# ===========================
# 3) EDF PREEMPTIVE - SOLO PER ESPERIMENTI
# ===========================
def simulate_pedd_tardy_count(jobs: List[Job]) -> int:
    """
    Simula una schedula preemptive EDD (Earliest Due Date) e restituisce
    il numero di job tardy in quella schedula.

    IMPORTANTE:
    - Non garantisce l'ottimo del problema preemptive 1 | pmtn, r_j | sum U_j
    - Non deve essere usato come lower bound nel B&B
    """
    if not jobs:
        return 0

    jobs_by_release = sorted(jobs, key=lambda job: job.r)
    active_heap = []  # [due_date, remaining_time, job_id]
    t = jobs_by_release[0].r
    idx = 0
    tardy_count = 0

    while idx < len(jobs_by_release) or active_heap:
        # Rilascio job
        while idx < len(jobs_by_release) and jobs_by_release[idx].r <= t:
            job = jobs_by_release[idx]
            heapq.heappush(active_heap, [job.d, job.p, job.id])
            idx += 1

        if not active_heap:
            t = jobs_by_release[idx].r
            continue

        due_date, rem_time, job_id = heapq.heappop(active_heap)
        next_release = jobs_by_release[idx].r if idx < len(jobs_by_release) else float('inf')
        run_time = min(rem_time, next_release - t)
        t += run_time
        rem_time -= run_time

        if rem_time == 0:
            if t > due_date:
                tardy_count += 1
        else:
            heapq.heappush(active_heap, [due_date, rem_time, job_id])

    return tardy_count

# ===========================
# 4) LOWER BOUND LP (AMPL)
# ===========================
def compute_lb_lp(T, S, jobs, relax_model_file, data_file="instance.dat"):
    """
    Chiama AMPL per risolvere il modello rilassato fissando le decisioni dei job in T e S.
    """
    return run_ampl_relax_node(
        relax_model_file=relax_model_file,
        T=T,
        S=S,
        jobs=jobs,
        data_file=data_file
    )
