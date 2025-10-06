from typing import List, Set, Tuple, Optional
import time
from node import Node
from bbStats import BnBStats
from lower_bound.lower_bound import compute_lb_knapsack

# Soglie per attivare il bound knapsack
KP_N_MAX = 50       # max numero di job per invocarlo
KP_H_MAX = 500      # max valore di H=max(d_j) per invocarlo

best_int: Optional[int] = None
best_solutions: List[Set[int]] = []

# Statistiche
stats = BnBStats()

def heuristic_upper_bound(jobs: List) -> Tuple[int, Set[int]]:
    """
    Euristica EDD non-preemptive con release: restituisce
    (numero tardy, insieme ID tardy).
    - ordina per due-date (tie-break su p crescente)
    - rispetta i r_j avanzando il tempo
    - marca tardy se C_j > d_j
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


def reset(jobs: List):
    """
    Inizializza best_int e la lista delle soluzioni ottime, azzera le statistiche.
    Conserva SEMPRE l'insieme vuoto se l'UB è 0 (fix vs falsy set()).
    """
    global best_int, best_solutions, stats
    best_int, first_sol = heuristic_upper_bound(jobs)
    best_solutions = [first_sol]          # <-- conserva anche set() vuoto
    stats.reset()


def branch_and_bound(node: Node,
                     jobs: List,
                     is_on_time_schedulable,
                     select_job):
    """
    Ricorsione Branch & Bound per 1|r_j|sum U_j con bound preemptive e knapsack.
    Inizializza SEMPRE anche il set dalla euristica, così
    se fai prune a radice (LB==UB) hai già T best.
    """
    global best_int, best_solutions, stats

    # Inizializza UB + set alla prima chiamata
    if best_int is None:
        best_int, first_sol = heuristic_upper_bound(jobs)
        best_solutions = [first_sol]      # <-- conserva anche set() vuoto

    # 1) Statistiche nodo
    stats.nodi_generati += 1
    stats.profondità_totale += node.depth

    # 2) Filtra i job ancora in gioco
    decided_jobs = node.T.union(node.S)
    jobs_remain = [job for job in jobs if job.id not in decided_jobs]

    # 2a) se S da solo è infeasible, taglia subito
    S_jobs = [j for j in jobs if j.id in node.S]
    if S_jobs and not is_on_time_schedulable(S_jobs):
        # se hai un contatore dedicato, usa quello; altrimenti segna come leaf
        if hasattr(stats, "fathom_infeasible"):
            stats.fathom_infeasible += 1
        else:
            stats.fathom_leaf += 1
        return

    # 3) Calcola lower bound preemptive (rilassato)
    start = time.time()
    if not jobs_remain:
        node.lb = 0
    else:
        # LB preemptive (PEDD-like) delegato al nodo, IGNORANDO l'interferenza di S (rilassamento)
        node.compute_lb(jobs_remain)

        # 3a) Knapsack LB se opportuno
        H = max((job.d for job in jobs_remain), default=0)
        if len(jobs_remain) <= KP_N_MAX or H <= KP_H_MAX:
            lb_kp = compute_lb_knapsack(jobs_remain)
            node.lb = max(node.lb, lb_kp)

    stats.tempo_totale_lb += time.time() - start
    stats.chiamate_lb += 1

    # 4) Pruning: bound totale (usa '>' per poter enumerare tutte le ottime)
    total_bound = len(node.T) + node.lb
    if total_bound > best_int:
        stats.fathom_lb += 1
        return

    # 5) Early-stop radice quando LB=0 (tutto on-time è possibile nel rilassamento)
    if node.depth == 0 and node.lb == 0:
        stats.fathom_leaf += 1
        best_int = 0
        best_solutions = [set()]
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

    # 7) Selezione job per branching: PASSA SOLO I RIMANENTI (coerente con F)
    k = select_job(node, jobs_remain)
    if k is None:
        return

    # 8) Branch 'on-time'
    child_ontime = Node(T=node.T.copy(), S=node.S.union({k}), depth=node.depth + 1)
    branch_and_bound(child_ontime, jobs, is_on_time_schedulable, select_job)

    # 9) Branch 'tardy'
    child_tardy = Node(T=node.T.union({k}), S=node.S.copy(), depth=node.depth + 1)
    branch_and_bound(child_tardy, jobs, is_on_time_schedulable, select_job)


def get_best_solution():
    """
    Restituisce il numero minimo di tardy e la lista di tutti i set di job tardy ottimi.
    """
    return best_int, best_solutions
