import time
from node import Node
from typing import List, Set
from bbStats import BnBStats

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

    # 1) Controlli di statistiche
    stats.nodi_generati += 1
    stats.profondità_totale += node.depth

    # 2) Prepara la lista dei job rimanenti (escludendo quelli già tardy)
    jobs_remain = [job for job in jobs if job.id not in node.T]

    # 3) Calcola il lower bound sui tardy per i job rimanenti
    start = time.time()
    node.compute_lb(jobs_remain)
    stats.tempo_totale_lb += time.time() - start
    stats.chiamate_lb += 1

    # 4) Pruning basato sul bound totale = |T| + lb
    total_bound = len(node.T) + node.lb
    if total_bound >= best_int:
        stats.fathom_lb += 1
        return

    # 5) Early-stop radice: se al radice LB=0, soluzione ottima è 0 tardy
    if node.depth == 0 and node.lb == 0:
        stats.fathom_leaf += 1
        best_int = 0
        best_sol = set()
        return

    # 6) Se è foglia ammissibile (LB=0 e schedulabilità non-preemptive OK)
    #    is_on_time_schedulable deve considerare solo jobs_remain e node.S
    if node.is_feasible_leaf(jobs_remain, is_on_time_schedulable):
        stats.fathom_leaf += 1
        tardy_count = len(node.T)
        if tardy_count < best_int:
            best_int = tardy_count
            best_sol = node.T.copy()
        return

    # 7) Branching: scegli un job non ancora fissato
    k = select_job(node, jobs_remain)
    if k is None:
        return

    # 8) Branch “k on-time” (fissiamo k in S) – passiamo sempre jobs_remain
    child_ontime = Node(T=node.T.copy(),
                        S=node.S.union({k}),
                        depth=node.depth + 1)
    branch_and_bound(child_ontime,
                     jobs_remain,
                     is_on_time_schedulable,
                     select_job)

    # 9) Branch “k tardy” (fissiamo k in T)
    child_tardy = Node(T=node.T.union({k}),
                       S=node.S.copy(),
                       depth=node.depth + 1)
    branch_and_bound(child_tardy,
                     jobs_remain,
                     is_on_time_schedulable,
                     select_job)

def get_best_solution():
    return best_int, best_sol
