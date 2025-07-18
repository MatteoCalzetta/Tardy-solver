from typing import Set, List
import LB  # Assunto: modulo con metodo compute_lb(jobs: List) -> float

class Node:
    def __init__(self, T: Set[int] = None, S: Set[int] = None, lb: float = 0.0, depth: int = 0):
        """
        Nodo di branching con:
        - T: job fissati come tardy
        - S: job fissati come on-time
        - lb: lower bound corrente
        - depth: profondità nell’albero
        """
        self.T = set(T) if T is not None else set()
        self.S = set(S) if S is not None else set()
        self.lb = lb
        self.depth = depth

    def compute_lb(self, jobs: List):
        """
        Calcola il lower bound su J \ T.
        jobs: lista di job (interi o oggetti) da cui si sottraggono quelli in T.
        """
        jobs_minus_T = [job for job in jobs if job not in self.T]
        self.lb = LB.compute_lb(jobs_minus_T)

    def is_feasible_leaf(self, jobs: List, is_on_time_schedulable) -> bool:
        """
        Verifica se è una foglia ammissibile:
        - lb == 0
        - tutti i job in S ∪ (J \ T) possono essere schedulati on-time

        jobs: lista completa J
        is_on_time_schedulable: funzione esterna che verifica se l'insieme è schedulabile
        """
        if self.lb != 0:
            return False
        candidate_S = self.S.union(job for job in jobs if job not in self.T)
        return is_on_time_schedulable(candidate_S)

    def __repr__(self):
        return f"Node(T={self.T}, S={self.S}, lb={self.lb}, depth={self.depth})"
