from job import Job
from node import Node
from bb import branch_and_bound, get_best_solution, stats
from util import is_on_time_schedulable, select_job


# Esempio di job
jobs = [
    Job(1, 0, 3, 5),
    Job(2, 1, 2, 6),
    Job(3, 2, 1, 4),
]

root = Node()

branch_and_bound(root, jobs, is_on_time_schedulable, select_job)

best_int, best_sol = get_best_solution()
print(f"Best tardy count: {best_int}")
print(f"Best tardy set: {sorted(best_sol)}")

stats.print_summary(best_int, best_sol)
