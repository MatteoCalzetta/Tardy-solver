# bb.py

from typing import List, Set, Tuple, Optional
import time
import sys
import os

# Aggiusta il path se necessario
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node import Node
from bbStats import BnBStats
from branch_and_bound.job import Job
from lower_bound.lower_bound import compute_lb_knapsack

# ==============================
# Soglie per attivare il knapsack
# ==============================
KP_N_MAX = 50       # max numero di job per invocarlo
KP_H_MAX = 500      # max H = max(d_j) per invocarlo

# ==========================
# Global per B&B
# ==========================
best_int: Optional[int] = None             # miglior numero di tardy trovato
best_solutions: List[Set[int]] = []        # lista dei set T ottimi
stats = BnBStats()                         # statistiche globali


# ==========================
# EURISTICA UPPER BOUND
# ==========================

def heuristic_upper_bound(jobs: List[Job]) -> Tuple[int, Set[int]]:
    """
    Euristica semplice (non-preemptive) per l'upper bound:
    - ordina per due-date (tie-break p crescente)
    - rispetta r_j avanzando il tempo
    - marca tardy se C_j > d_j

    Restituisce:
      (numero_tardy, insieme_ID_tardy)

    È solo un'euristica: serve per inizializzare best_int
    e avere una soluzione ammissibile da cui partire.
    """
    t = 0
    tardy_set: Set[int] = set()

    for job in sorted(jobs, key=lambda j: (j.d, j.p)):
        if t < job.r:
            t = job.r
        t += job.p
        if t > job.d:
            tardy_set.add(job.id)

    return len(tardy_set), tardy_set


# ==========================
# RESET GLOBALI
# ==========================

def reset(jobs: List[Job]) -> None:
    """
    Inizializza:
      - best_int (upper bound iniziale)
      - best_solutions (lista con il primo set ottimo trovato dall'euristica)
      - stats (statistiche a zero)

    Nota: conserva SEMPRE anche il set vuoto se l'UB è 0.
    """
    global best_int, best_solutions, stats

    best_int, first_sol = heuristic_upper_bound(jobs)
    best_solutions = [first_sol]    # conserva anche set() vuoto

    stats.reset()


# ==========================
# BRANCH AND BOUND
# ==========================

def branch_and_bound(node: Node,
                     jobs: List[Job],
                     is_on_time_schedulable,
                     select_job) -> None:
    """
    Ricorsione Branch & Bound per 1 | r_j | sum U_j.

    - Usa:
        * test di fattibilità di S via is_on_time_schedulable (es. EDD preemptive)
        * Knapsack come lower bound numerico (safe)
    - NON usa più EDD preemptive come LB numerico.
    """
    global best_int, best_solutions, stats

    # Inizializza UB + set alla prima chiamata
    if best_int is None:
        best_int, first_sol = heuristic_upper_bound(jobs)
        best_solutions = [first_sol]

    # 1) Statistiche nodo
    stats.nodi_generati += 1
    stats.profondità_totale += node.depth

    # 2) Job già decisi (S on-time, T tardy)
    decided_jobs = node.T.union(node.S)
    jobs_remain = [job for job in jobs if job.id not in decided_jobs]

    # 2a) Se S da solo è infeasible (nemmeno preemptive), taglia
    S_jobs = [j for j in jobs if j.id in node.S]
    if S_jobs and not is_on_time_schedulable(S_jobs):
        if hasattr(stats, "fathom_infeasible"):
            stats.fathom_infeasible += 1
        else:
            stats.fathom_leaf += 1
        return

    # 3) Calcolo lower bound (SOLO KNAPSACK)
    start = time.time()

    if not jobs_remain:
        node.lb = 0
    else:
        # Bound trivial: nel rilassamento potrebbero teoricamente essere tutti on-time => 0 tardy
        node.lb = 0

        # Knapsack LB se opportuno
        H = max((job.d for job in jobs_remain), default=0)
        if len(jobs_remain) <= KP_N_MAX or H <= KP_H_MAX:
            lb_kp = compute_lb_knapsack(jobs_remain)
            node.lb = max(node.lb, lb_kp)

    stats.tempo_totale_lb += time.time() - start
    stats.chiamate_lb += 1

    # 4) Pruning: bound totale
    #    (# tardy già fissati in T) + (minimo # tardy degli altri nel rilassamento)
    total_bound = len(node.T) + node.lb
    if total_bound > best_int:
        stats.fathom_lb += 1
        return

    # 5) Early-stop alla radice quando LB = 0 (tutti on-time possibili nel rilassamento)
    if node.depth == 0 and node.lb == 0:
        stats.fathom_leaf += 1
        best_int = 0
        best_solutions = [set()]   # tutti on-time
        return

    # 6) Foglia ammissibile (usa TUTTI i job, non solo i rimanenti)
    if node.is_feasible_leaf(jobs, is_on_time_schedulable):
        stats.fathom_leaf += 1
        tardy_count = len(node.T)

        if tardy_count < best_int:
            best_int = tardy_count
            best_solutions = [node.T.copy()]
        elif tardy_count == best_int:
            Tcopy = node.T.copy()
            if Tcopy not in best_solutions:
                best_solutions.append(Tcopy)
        return

    # 7) Selezione job per branching: passa solo i rimanenti (F)
    k = select_job(node, jobs_remain)
    if k is None:
        return

    # 8) Branch 'on-time'
    child_ontime = Node(T=node.T.copy(), S=node.S.union({k}), depth=node.depth + 1)
    branch_and_bound(child_ontime, jobs, is_on_time_schedulable, select_job)

    # 9) Branch 'tardy'
    child_tardy = Node(T=node.T.union({k}), S=node.S.copy(), depth=node.depth + 1)
    branch_and_bound(child_tardy, jobs, is_on_time_schedulable, select_job)


# ==========================
# ACCESSOR RISULTATI
# ==========================

def get_best_solution():
    """
    Restituisce:
      - numero minimo di tardy (best_int)
      - lista di tutti i set T ottimi
    """
    return best_int, best_solutions
