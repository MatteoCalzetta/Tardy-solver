from __future__ import annotations

from typing import List, Set, Tuple, Callable, Optional
import time

from node import Node
from bbStats import BnBStats
from lower_bound.lower_bound import compute_lb_knapsack


class BranchAndBoundScheduler:
    """
    Branch & Bound per 1|r_j|sum U_j con:
    - nodi definiti da S (on-time) e T (tardy);
    - UB euristico (EDD con release);
    - LB rilassati (preemptive via node.compute_lb + opzionale knapsack);
    - pruning configurabile.

    Assunzioni sugli oggetti job:
      job.id : int
      job.r  : int | float   (release date)
      job.p  : int | float   (processing time)
      job.d  : int | float   (due date)

    Assunzioni su Node:
      Node(T: Set[int], S: Set[int], depth: int)
      .T, .S : set di ID job
      .depth : profondità nell'albero
      .lb    : lower bound sul numero di tardy tra i rimanenti (può essere scritto qui)
      .compute_lb(jobs_remain: List[Job]) -> None  # calcola un LB rilassato e lo salva in .lb
      .is_feasible_leaf(jobs: List[Job], is_on_time_schedulable: Callable) -> bool
    """

    def __init__(
        self,
        kp_n_max: int = 50,
        kp_h_max: int = 500,
        knapsack_trigger: str = "and",
        prune_ge: bool = False,
        stats: Optional[BnBStats] = None,
    ) -> None:
        """
        :param kp_n_max: Soglia sul #job rimanenti per attivare il bound knapsack
        :param kp_h_max: Soglia su H=max(d_j) dei rimanenti per attivare il bound knapsack
        :param knapsack_trigger: 'and' per attivare solo se (n<=kp_n_max AND H<=kp_h_max),
                                 'or' per attivare se (n<=kp_n_max OR H<=kp_h_max)
        :param prune_ge: Se True usa pruning con >= (più aggressivo, non enumera tutte le ottime).
                         Se False usa > (consente enumerazione di tutte le ottime).
        :param stats: Oggetto BnBStats esterno (se None, ne istanzia uno interno).
        """
        assert knapsack_trigger in ("and", "or")
        self.kp_n_max = kp_n_max
        self.kp_h_max = kp_h_max
        self.knapsack_trigger = knapsack_trigger
        self.prune_ge = prune_ge

        self.best_int: Optional[int] = None
        self.best_solutions: List[Set[int]] = []
        self.stats: BnBStats = stats if stats is not None else BnBStats()

    # -----------------------
    # API PUBBLICA
    # -----------------------

    def reset(self, jobs: List) -> None:
        """
        Inizializza UB tramite euristica e azzera statistiche.
        Conserva l'insieme vuoto se l'UB è 0 (fix vs falsy set()).
        """
        self.best_int, first_sol = self.heuristic_upper_bound(jobs)
        self.best_solutions = [first_sol]  # <-- conserva anche set() vuoto
        self._stats_reset_safe()

    def solve(
        self,
        jobs: List,
        is_on_time_schedulable: Callable[[List], bool],
        select_job: Callable[[Node, List], Optional[int]],
        root: Optional[Node] = None,
    ) -> Tuple[int, List[Set[int]]]:
        """
        Esegue il B&B a partire dalla radice (o da un nodo dato).
        :return: (ottimo, lista di insiemi T ottimi)
        """
        if root is None:
            root = Node(T=set(), S=set(), depth=0)

        # Init UB se non già fatto
        if self.best_int is None:
            self.best_int, first_sol = self.heuristic_upper_bound(jobs)
            self.best_solutions = [first_sol]  # <-- conserva set() vuoto

        self._branch_and_bound(root, jobs, is_on_time_schedulable, select_job)
        # best_int non dovrebbe mai essere None qui
        return int(self.best_int), self.best_solutions

    def get_best_solution(self) -> Tuple[Optional[int], List[Set[int]]]:
        """Restituisce (numero minimo di tardy, lista di T ottimi)."""
        return self.best_int, self.best_solutions

    # -----------------------
    # IMPLEMENTAZIONE
    # -----------------------

    @staticmethod
    def heuristic_upper_bound(jobs: List) -> Tuple[int, Set[int]]:
        """
        Euristica EDD non-preemptive con release:
        - ordina per due date (tie-break su p crescente),
        - rispetta i r_j avanzando il tempo,
        - marca tardy se C_j > d_j.
        Ritorna (numero tardy, insieme IDs tardy).
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

    def _branch_and_bound(
        self,
        node: Node,
        jobs: List,
        is_on_time_schedulable: Callable[[List], bool],
        select_job: Callable[[Node, List], Optional[int]],
    ) -> None:
        # 1) Statistiche nodo
        self._inc_stat("nodi_generati", 1)
        self._inc_stat("profondità_totale", node.depth)

        # 2) Filtra i job ancora in gioco
        decided_jobs = node.T.union(node.S)
        jobs_remain = [job for job in jobs if job.id not in decided_jobs]

        # 2a) Se S da solo è infeasible, taglia subito (contatore dedicato se disponibile)
        S_jobs = [j for j in jobs if j.id in node.S]
        if S_jobs and (not is_on_time_schedulable(S_jobs)):
            if self._has_stat("fathom_infeasible"):
                self._inc_stat("fathom_infeasible", 1)
            else:
                # fallback su fathom_leaf se non esiste il contatore dedicato
                self._inc_stat("fathom_leaf", 1)
            return

        # 3) Calcola lower bound sui rimanenti (rilassato)
        start_lb = time.time()
        if not jobs_remain:
            node.lb = 0
        else:
            # LB preemptive (PEDD-like) delegato al nodo, IGNORANDO l'interferenza di S (rilassamento)
            node.compute_lb(jobs_remain)

            # 3a) LB knapsack se opportuno
            H = max((job.d for job in jobs_remain), default=0)
            if self._should_run_knapsack(len(jobs_remain), H):
                lb_kp = compute_lb_knapsack(jobs_remain)
                node.lb = max(node.lb, lb_kp)

        self._inc_stat("tempo_totale_lb", time.time() - start_lb)
        self._inc_stat("chiamate_lb", 1)

        # 4) Pruning: bound totale
        total_bound = len(node.T) + node.lb
        if (self.prune_ge and total_bound >= self.best_int) or (not self.prune_ge and total_bound > self.best_int):
            self._inc_stat("fathom_lb", 1)
            return

        # 5) Early-stop radice quando LB=0 (tutto on-time possibile nel rilassamento)
        if node.depth == 0 and node.lb == 0:
            self.best_int = 0
            self.best_solutions = [set()]
            if self._has_stat("fathom_root"):
                self._inc_stat("fathom_root", 1)
            else:
                self._inc_stat("fathom_leaf", 1)
            return

        # 6) Foglia ammissibile (usa TUTTI i job)
        if node.is_feasible_leaf(jobs, is_on_time_schedulable):
            tardy_count = len(node.T)
            if tardy_count < self.best_int:
                self.best_int = tardy_count
                self.best_solutions = [node.T.copy()]
            elif tardy_count == self.best_int:
                Tcopy = node.T.copy()
                if Tcopy not in self.best_solutions:
                    self.best_solutions.append(Tcopy)
            self._inc_stat("fathom_leaf", 1)
            return

        # 7) Selezione job per branching: PASSA SOLO I RIMANENTI (fix)
        k = select_job(node, jobs_remain)
        if k is None:
            return

        # 8) Branch 'on-time'
        child_ontime = Node(T=node.T.copy(), S=node.S.union({k}), depth=node.depth + 1)
        self._branch_and_bound(child_ontime, jobs, is_on_time_schedulable, select_job)

        # 9) Branch 'tardy'
        child_tardy = Node(T=node.T.union({k}), S=node.S.copy(), depth=node.depth + 1)
        self._branch_and_bound(child_tardy, jobs, is_on_time_schedulable, select_job)

    # -----------------------
    # UTILS
    # -----------------------

    def _should_run_knapsack(self, n: int, H: float) -> bool:
        """Decide se invocare il bound knapsack in base al trigger configurato."""
        if self.knapsack_trigger == "and":
            return (n <= self.kp_n_max) and (H <= self.kp_h_max)
        else:  # 'or'
            return (n <= self.kp_n_max) or (H <= self.kp_h_max)

    def _stats_reset_safe(self) -> None:
        """Chiama stats.reset() se presente; altrimenti azzera i campi noti se esistono."""
        if hasattr(self.stats, "reset") and callable(self.stats.reset):
            self.stats.reset()
            return
        # fallback: prova ad azzerare alcuni campi frequenti se esistono
        for fld in (
            "nodi_generati",
            "profondità_totale",
            "tempo_totale_lb",
            "chiamate_lb",
            "fathom_lb",
            "fathom_leaf",
            "fathom_infeasible",
            "fathom_root",
        ):
            if hasattr(self.stats, fld):
                setattr(self.stats, fld, 0)

    def _inc_stat(self, name: str, delta) -> None:
        """Incrementa una statistica se esiste, altrimenti crea il campo (fallback)."""
        if hasattr(self.stats, name):
            setattr(self.stats, name, getattr(self.stats, name) + delta)
        else:
            # crea on the fly per non perdere l'informazione
            setattr(self.stats, name, delta)

    def _has_stat(self, name: str) -> bool:
        return hasattr(self.stats, name)
