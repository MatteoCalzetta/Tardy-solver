import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import lower_bound.lower_bound as LB

class Node:
    def __init__(self, T=None, S=None, depth=0):
        self.T = set(T) if T is not None else set()
        self.S = set(S) if S is not None else set()
        self.depth = depth

        # Lower bound separati
        self.lb_moore = 0
        self.lb_kp = 0
        self.lb_lp = 0

        # Lower bound effettivo per il pruning
        self.lb_best = 0

    # ===== BOUND ESISTENTI =====
    def compute_lb_moore(self, jobs):
        jobs_minus_T = [j for j in jobs if j.id not in self.T]
        self.lb_moore = LB.compute_lb_moore(jobs_minus_T)

    def compute_lb_KP(self, jobs):
        jobs_minus_T = [j for j in jobs if j.id not in self.T]
        self.lb_kp = LB.compute_lb_knapsack(jobs_minus_T)

    # ===== NUOVO BOUND LP =====
    def compute_lb_lp(self, jobs, relax_model_file, data_file="instance.dat"):
        self.lb_lp = LB.compute_lb_lp(
            T=self.T,
            S=self.S,
            jobs=jobs,
            relax_model_file=relax_model_file,
            data_file=data_file
        )

    # ===== COMBINAZIONE =====
    def compute_all_bounds(self, jobs, relax_model_file, data_file="instance.dat"):
        """Calcola TUTTI i lower bound e salva il migliore."""
        self.compute_lb_moore(jobs)
        self.compute_lb_KP(jobs)
        self.compute_lb_lp(jobs, relax_model_file, data_file)
        self.lb_best = max(self.lb_moore, self.lb_kp, self.lb_lp)

    def is_feasible_leaf(self, jobs, is_on_time_schedulable):
        if self.lb_best != 0:
            return False
        candidate_S = self.S.union(j.id for j in jobs if j.id not in self.T)
        job_subset = [j for j in jobs if j.id in candidate_S]
        return is_on_time_schedulable(job_subset)

    def __repr__(self):
        return (
            f"Node(T={self.T}, S={self.S}, depth={self.depth}, "
            f"LB_moore={self.lb_moore}, "
            f"LB_KP={self.lb_kp}, "
            f"LB_LP={self.lb_lp}, "
            f"LB_best={self.lb_best})"
        )
