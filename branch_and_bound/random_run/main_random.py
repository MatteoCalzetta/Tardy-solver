import re
import sys
import os
import time
import subprocess
from typing import List, Tuple

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from job_generator import JobGenerator
from node import Node
from bb import branch_and_bound, get_best_solution, stats
from util import is_on_time_schedulable, select_job

# ----------------- utility I/O sicure -----------------
def read_int(prompt: str, default: int = None, min_val: int = None) -> int:
    s = input(prompt).strip()
    if s == "" and default is not None:
        return default
    try:
        v = int(s)
        if min_val is not None and v < min_val:
            print(f"Valore troppo piccolo, uso {min_val}.")
            return min_val
        return v
    except Exception:
        if default is not None:
            print(f"Input non valido, uso default {default}.")
            return default
        raise

def read_float(prompt: str, default: float = None, min_val: float = None) -> float:
    s = input(prompt).strip()
    if s == "" and default is not None:
        return default
    try:
        v = float(s)
        if min_val is not None and v < min_val:
            print(f"Valore troppo piccolo, uso {min_val}.")
            return min_val
        return v
    except Exception:
        if default is not None:
            print(f"Input non valido, uso default {default}.")
            return default
        raise
# ------------------------------------------------------

# ---------- Funzione per esportare jobs in formato AMPL ----------
def export_to_ampl_dat(jobs, filename="instance.dat"):
    n = len(jobs)
    total_p = sum(job.p for job in jobs)
    H = max(job.r for job in jobs) + total_p  # Upper bound corretto

    with open(filename, "w") as f:
        f.write(f"param n := {n};\n")
        f.write(f"param H := {H};\n\n")

        # release dates
        f.write("param r :=\n")
        for i, job in enumerate(jobs, start=1):
            f.write(f"  {i} {job.r}\n")
        f.write(";\n\n")

        # processing times
        f.write("param p :=\n")
        for i, job in enumerate(jobs, start=1):
            f.write(f"  {i} {job.p}\n")
        f.write(";\n\n")

        # due dates
        f.write("param d :=\n")
        for i, job in enumerate(jobs, start=1):
            f.write(f"  {i} {job.d}\n")
        f.write(";\n")

    print(f"File '{filename}' esportato per AMPL con H={H}.")

# ---------- Funzione per eseguire AMPL ----------
def run_ampl(model_file="/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl_model/model.mod",
             data_file="instance.dat",
             solver="gurobi"):

    ampl_exe = "/home/giulia/Documenti/AMOD_project/ampl.linux-intel64/ampl"
    run_file = "run_ampl.run"

    ampl_script = f"""
reset;
option solver {solver};

model "{model_file}";
data "{data_file}";

solve;

print "===================================";
print " RISULTATI AMPL";
print "===================================";

# Mostra stato di risoluzione e valore ottimo
display sum{{j in JOBS}} U[j];

print "---- Job tardivi (U[j]) ----";
display U;

print "---- Job completati (x[j,t]=1) ----";
for {{j in JOBS, t in 0..H: x[j,t] > 0.5}} {{
    printf "Job %d termina a t=%d\\n", j, t;
}}
"""

    with open(run_file, "w") as f:
        f.write(ampl_script)

    try:
        result = subprocess.run(
            [ampl_exe, run_file],
            capture_output=True,
            text=True,
            check=True
        )
    except FileNotFoundError:
        print(f"Eseguibile AMPL non trovato: {ampl_exe}")
        return None
    except subprocess.CalledProcessError as e:
        print("Errore durante l'esecuzione AMPL:")
        print(e.stderr)
        return None

    print("\n===== OUTPUT COMPLETO AMPL =====")
    print(result.stdout)
    print("==================================\n")

    # Estrai risultato totale tardy
    match = re.search(r"sum\{j in JOBS\} U\[j\]\s*=\s*([0-9]+)", result.stdout)
    if match:
        tardy_count = int(match.group(1))
        print(f"Risultato AMPL ({solver}): {tardy_count}")
        return tardy_count
    else:
        print("Impossibile leggere il risultato AMPL:")
        print(result.stdout)
        return None

# ---------------- MAIN ----------------
def main():
    print("== Generazione Job ==")
    print("Modalità:")
    print("  1) tight  (scadenze strette: ritardi probabili)")
    print("  2) wide   (scadenze larghe: pochi ritardi)")
    print("  3) mix    (misto 70% tight, 30% wide)")
    print("  4) overloaded (blocchi sovraccarichi: ritardi garantiti)")

    choice = input("Seleziona [1-4] (default 1): ").strip() or "1"

    generator = JobGenerator(seed=42)

    # ---------------- Generazione job ----------------
    if choice == "4":
        n_target = read_int("Quanti job totali desideri circa? (default 20): ", default=20, min_val=1)
        num_blocks = read_int("Quanti blocchi sovraccarichi? (default 1): ", default=1, min_val=1)
        blocks: List[Tuple[int, int, float]] = []
        for b in range(num_blocks):
            default_start = b * 30
            start = read_int(f" Blocco {b+1} - start (default {default_start}): ", default=default_start)
            length = read_int(f" Blocco {b+1} - length (default 20): ", default=20, min_val=1)
            overload = read_float(f" Blocco {b+1} - overload > 1 (default 1.3): ", default=1.3, min_val=1.0001)
            blocks.append((start, length, overload))

        block_jobs = generator.generate_overloaded_blocks(
            blocks=blocks,
            p_range=(1, 5),
            release_spread=0.4,
            extra_jobs=0,
        )

        if len(block_jobs) >= n_target:
            jobs = block_jobs
        else:
            extras_needed = n_target - len(block_jobs)
            extra_jobs = generator.generate(
                n_jobs=extras_needed,
                r_range=(0, 100),
                p_range=(1, 5),
                tightness=1.5,
                mode="wide",
            )
            jobs = block_jobs + extra_jobs
    else:
        n = read_int("\nQuanti job vuoi generare? ", default=20, min_val=1)
        r_min = read_int("Intervallo r: min (default 0): ", default=0)
        r_max = read_int("Intervallo r: max (default 100): ", default=100, min_val=r_min)
        p_min = read_int("Intervallo p: min (default 1): ", default=1, min_val=1)
        p_max = read_int("Intervallo p: max (default 5): ", default=5, min_val=p_min)

        if choice == "2":
            mode = "wide"
            tightness = 0.5
        elif choice == "3":
            mode = "mix"
            tightness = 0.2
        else:
            mode = "tight"
            tightness = read_float("Tightness ∈ [0..1+] (default 0.2): ", default=0.2, min_val=0.0)

        jobs = generator.generate(
            n_jobs=n,
            r_range=(r_min, r_max),
            p_range=(p_min, p_max),
            tightness=tightness,
            mode=mode,
        )

    # ---------------- Stampa e Branch & Bound ----------------
    print("\n== JOB GENERATI ==")
    for job in jobs:
        print(job)

    root = Node()   # se necessario: Node(T=set(), S=set(), depth=0)

    start_appr = time.time()
    branch_and_bound(root, jobs, is_on_time_schedulable, select_job)
    end_appr = time.time()
    processing_time_appr = end_appr - start_appr

    best_int, all_T_sets = get_best_solution()
    print(f"\nBest tardy count: {best_int}")

    # Stampa robusta dei set ottimi
    if not all_T_sets:
        print("Best tardy set: []")
    elif len(all_T_sets) == 1:
        print(f"Best tardy set: {sorted(next(iter(all_T_sets)))}")
    else:
        print(f"All optimal tardy sets ({len(all_T_sets)}): {[sorted(s) for s in all_T_sets]}")

    print(f"\nElapsing time for B&B: {processing_time_appr:.6f}s")

    # Per compatibilità con print_summary che si aspetta (forse) un solo set:
    first_set = all_T_sets[0] if all_T_sets else set()
    stats.print_summary(best_int, first_set)

    # ---------------- Risoluzione AMPL ----------------
    export_to_ampl_dat(jobs)

    start_ampl = time.time()
    ampl_tardy = run_ampl(
        model_file="/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl_model/model.mod",
        data_file="instance.dat",
        solver="gurobi"
    )
    end_ampl = time.time()
    processing_time_ampl = end_ampl - start_ampl
    print(f"Elapsing time for AMPL model: {processing_time_ampl:.6f}s")

    if ampl_tardy is not None:
        print(f"\n Risultato AMPL (Gurobi): {ampl_tardy}")
        print(f" Risultato Branch & Bound: {best_int}")

if __name__ == "__main__":
    main()
