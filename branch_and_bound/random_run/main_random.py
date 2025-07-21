import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from job_generator import JobGenerator
from node import Node
from bb import branch_and_bound, get_best_solution, stats
from util import is_on_time_schedulable, select_job

def main():
    try:
        n = int(input("Quanti job vuoi generare? "))
    except ValueError:
        print("Input non valido. Inserisci un intero.")
        return

    generator = JobGenerator(seed=42)
    jobs = generator.generate(n_jobs=n, tight_due_dates=False)

    print("\n== JOB GENERATI ==")
    for job in jobs:
        print(job)

    root = Node()
    branch_and_bound(root, jobs, is_on_time_schedulable, select_job)

    best_int, best_sol = get_best_solution()
    print(f"\nBest tardy count: {best_int}")
    print(f"Best tardy set: {sorted(best_sol)}\n")

    stats.print_summary(best_int, best_sol)

if __name__ == "__main__":
    main()
