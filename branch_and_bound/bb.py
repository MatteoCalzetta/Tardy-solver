# bb.py
#
# Branch & Bound per 1|r_j|sum U_j.
# - Stato di ciascun nodo: insiemi S (on-time), T (tardy), F = J\(S∪T).
# - UB: euristica EDD non-preemptive con release.
# - LB: rilassamento preemptive ispirato a Lawler (overload di intervallo + knapsack).

from typing import List, Set, Tuple, Optional
import time

from node import Node
from bbStats import BnBStats

# best_int = valore ottimo corrente (#tardy)
best_int: Optional[int] = None
# best_solutions = lista di insiemi T ottimi
best_solutions: List[Set[int]] = []

# Statistiche globali
stats = BnBStats()


def heuristic_upper_bound(jobs: List) -> Tuple[int, Set[int]]:
    """
    Euristica EDD non-preemptive con release:
    - ordina i job per due-date (tie-break su p crescente),
    - rispetta i r_j avanzando il tempo,
    - marca tardy ogni job con C_j > d_j.

    Ritorna:
      (numero tardy, insieme ID tardy).
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


def reset(jobs: List) -> None:
    """
    Inizializza best_int e la lista delle soluzioni ottime tramite l'euristica EDD,
    azzera le statistiche.
    Conserva SEMPRE l'insieme vuoto se l'UB è 0 (fix vs falsy set()).
    """
    global best_int, best_solutions, stats
    best_int, first_sol = heuristic_upper_bound(jobs)
    # first_sol può essere anche set() (tutti on-time); in ogni caso va conservato
    best_solutions = [first_sol]
    stats.reset()


def branch_and_bound(node: Node,
                     jobs: List,
                     is_on_time_schedulable,
                     select_job) -> None:
    """
    Ricorsione Branch & Bound per 1|r_j|sum U_j.

    Stato del nodo:
      - node.S: job forzati on-time,
      - node.T: job forzati tardy,
      - jobs_remain = F = job non ancora decisi.

    UB: euristica EDD globale (inizializzata alla prima chiamata).
    LB: rilassamento preemptive ispirato a Lawler, calcolato su F, tramite
        lower_bound.lower_bound.compute_lb_combined.

    Il pruning usa la regola:
      |T| + LB(F) > best_int   => potatura (non può battere la soluzione corrente).
    """
    global best_int, best_solutions, stats

    # Inizializza UB + set alla prima chiamata (se reset non è stato invocato)
    if best_int is None:
        best_int, first_sol = heuristic_upper_bound(jobs)
        best_solutions = [first_sol]

    # 1) Statistiche nodo
    stats.nodi_generati += 1
    stats.profondità_totale += node.depth

    # 2) Filtra i job ancora in gioco: F = J\(S ∪ T)
    decided_jobs = node.T.union(node.S)
    jobs_remain = [job for job in jobs if job.id not in decided_jobs]

    # 2a) Se S da solo è infeasible (neppure i job in S possono stare on-time), taglia subito
    S_jobs = [j for j in jobs if j.id in node.S]
    if S_jobs and not is_on_time_schedulable(S_jobs):
        if hasattr(stats, "fathom_infeasible"):
            stats.fathom_infeasible += 1
        else:
            stats.fathom_leaf += 1
        return

    # 3) Calcola lower bound (rilassamento preemptive alla Lawler: overload + knapsack)
    start = time.time()
    if not jobs_remain:
        node.lb = 0
    else:
        # import locale per evitare dipendenze circolari
        from lower_bound.lower_bound import compute_lb_combined
        node.lb = compute_lb_combined(jobs_remain)
    stats.tempo_totale_lb += time.time() - start
    stats.chiamate_lb += 1

    # 4) Pruning: bound totale (usa '>' per enumerare tutte le soluzioni ottime)
    total_bound = len(node.T) + node.lb
    if total_bound > best_int:
        stats.fathom_lb += 1
        return

    # 5) Early-stop alla radice quando LB=0 (rilassamento suggerisce tutti on-time possibili)
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

    # 7) Selezione job per branching: scegli k in F (jobs_remain)
    k = select_job(node, jobs_remain)
    if k is None:
        return

    # 8) Branch 'on-time' (aggiungo k a S)
    child_ontime = Node(T=node.T.copy(), S=node.S.union({k}), depth=node.depth + 1)
    branch_and_bound(child_ontime, jobs, is_on_time_schedulable, select_job)

    # 9) Branch 'tardy' (aggiungo k a T)
    child_tardy = Node(T=node.T.union({k}), S=node.S.copy(), depth=node.depth + 1)
    branch_and_bound(child_tardy, jobs, is_on_time_schedulable, select_job)


def get_best_solution():
    """
    Restituisce:
      - numero minimo di job tardy (best_int),
      - lista di tutti i set di job tardy ottimi (best_solutions).
    """
    return best_int, best_solutions
