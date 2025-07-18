import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import lower_bound.lower_bound as LB

class Node:
    def __init__(self, T=None, S=None, lb=0.0, depth=0):
        self.T = set(T) if T is not None else set()
        self.S = set(S) if S is not None else set()
        self.lb = lb
        self.depth = depth

    def compute_lb(self, jobs):
        jobs_minus_T = [j for j in jobs if j.id not in self.T]
        self.lb = LB.compute_lb(jobs_minus_T)

    def is_feasible_leaf(self, jobs, is_on_time_schedulable):
        if self.lb != 0:
            return False
        candidate_S = self.S.union(j.id for j in jobs if j.id not in self.T)
        job_subset = [j for j in jobs if j.id in candidate_S]
        return is_on_time_schedulable(job_subset)

    def __repr__(self):
        return f"Node(T={self.T}, S={self.S}, lb={self.lb}, depth={self.depth})"
