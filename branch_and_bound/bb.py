import time
from node import Node
from typing import List, Set
from bbStats import BnBStats
from lower_bound.lower_bound import compute_lb_knapsack

# Soglie per attivare il bound knapsack
KP_N_MAX = 50       # max numero di job per invocarlo
KP_H_MAX = 500      # max valore di H=max(d_j) per invocarlo

# Stato globale
best_int = float('inf')   # minimizziamo il numero di tardy
best_sol: Set[int] = set()

# Statistiche
stats = BnBStats()

def reset():
    global best_int, best_sol, stats
    best_int = float('inf')
    best_sol = set()
    stats.reset()

def branch_and_bound(node: Node,
                     jobs: List,
                     is_on_time_schedulable,
                     select_job):
    global best_int, best_sol, stats

    # 1) Statistiche nodo
    stats.nodi_generati += 1
    stats.profondità_totale += node.depth

    # 2) Filtra i job ancora in gioco
    jobs_remain = [job for job in jobs if job.id not in node.T]

    # 3) Calcola il lower bound preemptive (EDF)
    start = time.time()
    node.compute_lb(jobs_remain)

    # 3a) Se è piccolo o orizzonte contenuto, prova anche il knapsack
    H = max((job.d for job in jobs_remain), default=0)
    if len(jobs_remain) <= KP_N_MAX or H <= KP_H_MAX:
        lb_kp = compute_lb_knapsack(jobs_remain)
        node.lb = max(node.lb, lb_kp)

    stats.tempo_totale_lb += time.time() - start
    stats.chiamate_lb += 1

    # 4) Pruning: |T| + lb ≥ best_int → scarta
    total_bound = len(node.T) + node.lb
    if total_bound >= best_int:
        stats.fathom_lb += 1
        return

    # 5) Early‐stop radice
    if node.depth == 0 and node.lb == 0:
        stats.fathom_leaf += 1
        best_int = 0
        best_sol = set()
        return

    # 6) Foglia ammissibile
    if node.is_feasible_leaf(jobs_remain, is_on_time_schedulable):
        stats.fathom_leaf += 1
        tardy_count = len(node.T)
        if tardy_count < best_int:
            best_int = tardy_count
            best_sol = node.T.copy()
        return

    # 7) Branching: seleziona un job k
    k = select_job(node, jobs_remain)
    if k is None:
        return

    # 8) Ramo “k on-time”
    child_ontime = Node(T=node.T.copy(),
                        S=node.S.union({k}),
                        depth=node.depth + 1)
    branch_and_bound(child_ontime,
                     jobs_remain,
                     is_on_time_schedulable,
                     select_job)

    # 9) Ramo “k tardy”
    child_tardy = Node(T=node.T.union({k}),
                       S=node.S.copy(),
                       depth=node.depth + 1)
    branch_and_bound(child_tardy,
                     jobs_remain,
                     is_on_time_schedulable,
                     select_job)

def get_best_solution():
    return best_int, best_sol
