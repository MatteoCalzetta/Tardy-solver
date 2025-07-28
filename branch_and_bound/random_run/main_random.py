import sys
import os
import subprocess 

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from job_generator import JobGenerator
from node import Node
from bb import branch_and_bound, get_best_solution, stats
from util import is_on_time_schedulable, select_job

AMPL_PATH = "/home/giulia/Documenti/AMOD_project/ampl.linux-intel64/ampl"  
script_path = "/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl_model/run_ampl.run"

def write_ampl_dat_file(jobs, filename="/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl_model/instance.dat"):
    n = len(jobs)
    with open(filename, "w") as f:
        f.write(f"param n := {n};\n")
        f.write("param r :=\n")
        for i, job in enumerate(jobs, 1):
            f.write(f"  {i} {job.r}\n")
        f.write(";\n")

        f.write("param p :=\n")
        for i, job in enumerate(jobs, 1):
            f.write(f"  {i} {job.p}\n")
        f.write(";\n")

        f.write("param d :=\n")
        for i, job in enumerate(jobs, 1):
            f.write(f"  {i} {job.d}\n")
        f.write(";\n")

def run_ampl():
    ampl_dir = "/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl_model"
    try:
        result = subprocess.run([AMPL_PATH, script_path], check=True, capture_output=True, text=True, cwd=ampl_dir)
        print("=== Risultato AMPL ===")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Errore nell'esecuzione di AMPL:")
        print(e.stdout)
        print(e.stderr)

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

    # Salva dati in .dat
    write_ampl_dat_file(jobs, "/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl_model/instance.dat")

    # Esegui AMPL
    run_ampl()

if __name__ == "__main__":
    main()
