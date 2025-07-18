import time
from node import Node
from typing import List, Set
from bbStats import BnBStats

# Stato globale
best_int = float('-inf')
best_sol: Set[int] = set()

# Statistiche
stats = BnBStats()

def reset():
    global best_int, best_sol, stats
    best_int = float('-inf')
    best_sol = set()
    stats.reset()

def branch_and_bound(node: Node, jobs: List, is_on_time_schedulable, select_job):
    global best_int, best_sol, stats

    stats.nodi_generati += 1
    stats.profondità_totale += node.depth

    start = time.time()
    node.compute_lb(jobs)
    stats.tempo_totale_lb += time.time() - start
    stats.chiamate_lb += 1

    if node.lb <= best_int:
        stats.fathom_lb += 1
        return

    if node.is_feasible_leaf(jobs, is_on_time_schedulable):
        stats.fathom_leaf += 1
        tardy_count = len(node.T)
        if tardy_count > best_int:
            best_int = tardy_count
            best_sol = node.T.copy()
        return

    k = select_job(node, jobs)
    if k is None:
        return

    # Branch “k on-time” (esplorato per primo)
    child_ontime = Node(T=node.T.copy(), S=node.S.union({k}), depth=node.depth + 1)
    branch_and_bound(child_ontime, jobs, is_on_time_schedulable, select_job)

    # Branch “k tardy”
    child_tardy = Node(T=node.T.union({k}), S=node.S.copy(), depth=node.depth + 1)
    branch_and_bound(child_tardy, jobs, is_on_time_schedulable, select_job)

def get_best_solution():
    return best_int, best_sol
