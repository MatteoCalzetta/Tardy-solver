import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from job import Job
from node import Node
from bb import branch_and_bound, get_best_solution, stats
from util import is_on_time_schedulable, select_job
from amplpy import AMPL, add_to_path

add_to_path(r"/Users/giuliaboccuccia/Documents/AMOD/AMPL")

# === Scegli modalità: "bb" per branch-and-bound, "ampl" per solver AMPL ===#
#MODE = "ampl"  # cambiare in "bb" se vuoi usare branch-and-bound

# Esempio di job
jobs = [
    Job(1, 0, 4, 3),
    Job(2, 0, 3, 2),
    Job(3, 2, 1, 6),
    Job(4, 3, 2, 8),
    Job(5, 5, 1, 7),
]

def run_bb():
    print("=== Risoluzione con Branch-and-Bound ===")
    root = Node()
    branch_and_bound(root, jobs, is_on_time_schedulable, select_job)

    best_int, best_sol = get_best_solution()
    print(f"\nBest tardy count: {best_int}")
    print(f"Best tardy set: {sorted(best_sol)}\n")
    stats.print_summary(best_int, best_sol)

def run_ampl():
    print("=== Risoluzione con AMPL ===")
    # --- AMPL ---
    ampl = AMPL()
    ampl.read("/Users/giuliaboccuccia/Documents/AMOD/Tardy-solver/ampl_model/model.mod")  # il file del tuo modello AMPL

     # --- Estrai dati per AMPL ---
    n = len(jobs)
    r = [job.r for job in jobs]
    p = [job.p for job in jobs]
    d = [job.d for job in jobs]

    H = max(max([r[i] + p[i] for i in range(n)]), max(d))


    ampl.get_parameter("n").set(n)
    ampl.get_parameter("H").set(H)
    ampl.get_parameter("r").setValues({i+1: r[i] for i in range(n)})
    ampl.get_parameter("p").setValues({i+1: p[i] for i in range(n)})
    ampl.get_parameter("d").setValues({i+1: d[i] for i in range(n)})



    ampl.set_option("solver", "highs")
    ampl.solve()

    print("\n== RISULTATI AMPL ==")
    print("Valore ottimo tardy:", ampl.get_objective("TotalTardy").value())

    U = ampl.get_variable("U")
    for j in range(1, n + 1):
        print(f"Job {j} tardy:", int(U[j].value()))

switch = {
    "bb": run_bb, 
    "ampl": run_ampl
}
while True:
    print("\nSeleziona modalità di risoluzione:")
    print("  bb   -> Branch-and-Bound")
    print("  ampl -> AMPL Solver")
    print("  exit -> Esci")
    MODE = input("Modalità: ").strip().lower()

    if MODE == "exit":
        print("Uscita dal programma.")
        break

    func = switch.get(MODE, None)
    if func:
        func()
    else:
        print("Modalità non riconosciuta. Usa 'bb', 'ampl' o 'exit'.")