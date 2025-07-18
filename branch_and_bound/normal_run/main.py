import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from job import Job
from node import Node
from bb import branch_and_bound, get_best_solution, stats
from util import is_on_time_schedulable, select_job


# Esempio di job
jobs = [
    Job(1, 0, 4, 3),
    Job(2, 0, 3, 2),
    Job(3, 2, 1, 6),
    Job(4, 3, 2, 8),
    Job(5, 5, 1, 7),
]

root = Node()

branch_and_bound(root, jobs, is_on_time_schedulable, select_job)

best_int, best_sol = get_best_solution()
print(f"Best tardy count: {best_int}")
print(f"Best tardy set: {sorted(best_sol)}")

stats.print_summary(best_int, best_sol)
