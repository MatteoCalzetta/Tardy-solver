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

    Idea (come suggerito dal professore):
      - si "dimenticano" le release date vere e proprie
      - si prende r_min = min r_j tra questi job
      - si immagina di poter iniziare a tempo r_min
      - si applica l'algoritmo di Moore su due-date "effettive":
            d_eff_j = d_j - r_min

    L'algoritmo di Moore, in questo contesto, calcola il numero minimo di job tardy
    nel problema rilassato SENZA release, quindi fornisce un vero lower bound
    per il problema con release (anche se spesso poco stringente).
    """
    n = len(jobs)
    if n == 0:
        return 0

    # 1) Trova il minimo r_j tra questi job
    r_min = min(job.r for job in jobs)

    # 2) Costruisci lista con due date "shiftate"
    #    (d_eff_j = d_j - r_min) per simulare l'avvio a tempo r_min
    jobs_eff = []
    for job in jobs:
        d_eff = job.d - r_min
        jobs_eff.append((d_eff, job.p, job.id))

    # 3) Ordina per due date effettive crescenti
    jobs_eff.sort(key=lambda x: x[0])

    # 4) Algoritmo di Moore-Hodgson:
    #    - si costruisce una schedula incrementale
    #    - si mantiene un max-heap sulle durate p_j
    #    - se si sfora la due-date, si toglie il job con p_j più grande
    t = 0
    max_heap = []  # conterrà tuple (-p_j, job_id)
    tardy_ids = set()

    for d_eff, p, job_id in jobs_eff:
        t += p
        heapq.heappush(max_heap, (-p, job_id))

        if t > d_eff:
            # si rimuove il job con processing time più grande
            neg_p_max, jid_max = heapq.heappop(max_heap)
            p_max = -neg_p_max
            t -= p_max
            tardy_ids.add(jid_max)

    # Il numero di job tardy nel problema rilassato è il lower bound
    return len(tardy_ids)


# ===========================
# 3) EDF PREEMPTIVE - SOLO PER ESPERIMENTI
# ===========================

def simulate_pedd_tardy_count(jobs: List[Job]) -> int:
    """
    Simula una schedula preemptive EDD (Earliest Due Date) e
    restituisce il numero di job tardy in QUELLA schedula.

    IMPORTANTE:
      - NON è garantito che questo sia l'ottimo del problema preemptive
        1 | pmtn, r_j | sum U_j (per quello servirebbe l'algoritmo di Lawler).
      - NON deve essere usato come lower bound nel B&B.
      - Può essere usato solo per analisi / esperimenti.
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
