import time
from node import Node
from typing import List, Set
from bbStats import BnBStats
from lower_bound.lower_bound import compute_lb_knapsack

# Soglie per attivare il bound knapsack
KP_N_MAX = 50       # max numero di job per invocarlo
KP_H_MAX = 500      # max valore di H=max(d_j) per invocarlo

# Stato globale: best_int inizializzato via euristica
best_int: int = None
best_sol: Set[int] = set()

# Statistiche
stats = BnBStats()

def heuristic_upper_bound(jobs: List) -> int:
    """
    Calcola un upper bound per il numero di job tardivi
    usando una schedulazione non-preemptive EDF.
    """
    sorted_jobs = sorted(jobs, key=lambda j: j.d)
    t = 0
    tardy_count = 0
    for job in sorted_jobs:
        if t < job.r:
            t = job.r
        t += job.p
        if t > job.d:
            tardy_count += 1
    return tardy_count


def reset(jobs: List):
    """
    Inizializza best_int con l'euristica e resetta le statistiche.
    """
    global best_int, best_sol, stats
    best_int = heuristic_upper_bound(jobs)
    best_sol = set()
    stats.reset()


def branch_and_bound(node: Node,
                     jobs: List,
                     is_on_time_schedulable,
                     select_job):
    """
    Ricorsione Branch & Bound per 1|r_j|sum U_j con bound preemptive + knapsack.
    """
    global best_int, best_sol, stats

    # Inizializza best_int al primo nodo se non impostato
    if best_int is None:
        best_int = heuristic_upper_bound(jobs)

    # 1) Statistiche nodo
    stats.nodi_generati += 1
    stats.profondità_totale += node.depth

    # 2) Job ancora da decidere
    decided_jobs = node.T.union(node.S)
    jobs_remain = [job for job in jobs if job.id not in decided_jobs]

    # 2a) Pruning rapido: l'insieme S (già forzato on-time) deve essere schedulabile
    S_jobs = [j for j in jobs if j.id in node.S]
    if S_jobs and not is_on_time_schedulable(S_jobs):
        stats.fathom_leaf += 1
        return

    # 3) Lower bound
    start = time.time()
    if not jobs_remain:
        node.lb = 0
        stats.tempo_totale_lb += time.time() - start
        stats.chiamate_lb += 1
    else:
        node.compute_lb(jobs_remain)

        # 3a) Knapsack LB se conviene
        H = max((job.d for job in jobs_remain), default=0)
        if len(jobs_remain) <= KP_N_MAX or H <= KP_H_MAX:
            lb_kp = compute_lb_knapsack(jobs_remain)
            if lb_kp is not None:
                node.lb = max(node.lb, lb_kp)

        stats.tempo_totale_lb += time.time() - start
        stats.chiamate_lb += 1

    # 4) Pruning: bound totale
    total_bound = len(node.T) + node.lb
    if total_bound >= best_int:
        stats.fathom_lb += 1
        return

    # 5) Early-stop in radice quando LB=0 (tutto on-time è possibile)
    if node.depth == 0 and node.lb == 0:
        stats.fathom_leaf += 1
        best_int = 0
        best_sol = set()
        return

    # 6) Foglia ammissibile — usa TUTTI i job (non solo jobs_remain!)
    if node.is_feasible_leaf(jobs, is_on_time_schedulable):
        stats.fathom_leaf += 1
        tardy_count = len(node.T)
        if tardy_count < best_int:
            best_int = tardy_count
            best_sol = node.T.copy()
        return

    # 7) Scelta del job per il branching
    k = select_job(node, jobs_remain)
    if k is None:
        return

    # 8) Branch 'on-time'
    child_ontime = Node(T=node.T.copy(), S=node.S.union({k}), depth=node.depth + 1)
    branch_and_bound(child_ontime, jobs, is_on_time_schedulable, select_job)

    # 8b) Skip intelligente: se abbiamo già raggiunto |T|, il ramo tardy non può migliorare
    if best_int == len(node.T):
        return

    # 9) Branch 'tardy'
    child_tardy = Node(T=node.T.union({k}), S=node.S.copy(), depth=node.depth + 1)
    branch_and_bound(child_tardy, jobs, is_on_time_schedulable, select_job)


def get_best_solution():
    """
    Restituisce il numero minimo di tardy e il set di job tardy.
    """
    return best_int, best_sol
