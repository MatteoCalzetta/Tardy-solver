import re
import sys
import os
import time
import csv 
import subprocess

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from job_generator import JobGenerator
from node import Node
from bb import branch_and_bound, get_best_solution, stats, reset
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

# ---------- Funzione per esportare jobs in formato AMPL ----------
def export_to_ampl_dat(jobs, filename="instance.dat"):
    """Esporta l'istanza in un file .dat per AMPL."""
    n = len(jobs)
    total_p = sum(job.p for job in jobs)
    H = max(job.r for job in jobs) + total_p  # Upper bound corretto

    with open(filename, "w") as f:
        # Definizione set JOBS
        f.write(f"set JOBS := {' '.join(str(i) for i in range(1, n+1))};\n\n")

        # Parametro H
        f.write(f"param H := {H};\n\n")

        # release dates
        f.write("param r :=\n")
        for i, job in enumerate(jobs, start=1):
            f.write(f" {i} {job.r}\n")
        f.write(";\n\n")

        # processing times
        f.write("param p :=\n")
        for i, job in enumerate(jobs, start=1):
            f.write(f" {i} {job.p}\n")
        f.write(";\n\n")

        # due dates
        f.write("param d :=\n")
        for i, job in enumerate(jobs, start=1):
            f.write(f" {i} {job.d}\n")
        f.write(";\n")

    print(f"File '{filename}' esportato per AMPL con H={H}.")

# ---------- Funzione per eseguire AMPL COMPLETO ----------
def run_ampl(model_file: str, data_file: str = "instance.dat", solver: str = "gurobi"):
    ampl_exe = "/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl.linux-intel64/ampl"
    run_file = "run_ampl_completo.run"
    ampl_script = f"""
reset;
option solver {solver};
model "{model_file}";
data "{data_file}";
solve;
print "===================================";
print " RISULTATI AMPL COMPLETO ";
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

# ---------- AMPL RILASSATO ----------
def run_ampl_relax_node(relax_model_file, T, S, jobs, data_file="instance.dat", solver="gurobi"):
    ampl_exe = "/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl.linux-intel64/ampl"
    run_file = "run_ampl_relax_node.run"

    fix_cmds = []
    # Fissa le variabili dei job già decisi
    for j in T:
        t = jobs[j-1].d + jobs[j-1].p  # tempo tardivo
        fix_cmds.append(f"fix x[{j},{t}] := 1;")
        fix_cmds.append(f"for {{t2 in 0..H: t2 != {t}}} fix x[{j},t2] := 0;")
        fix_cmds.append(f"fix U[{j}] := 1;")
    for j in S:
        t = jobs[j-1].d  # completamento on-time
        fix_cmds.append(f"fix x[{j},{t}] := 1;")
        fix_cmds.append(f"for {{t2 in 0..H: t2 != {t}}} fix x[{j},t2] := 0;")
        fix_cmds.append(f"fix U[{j}] := 0;")
    
    fix_block = "\n".join(fix_cmds)
    ampl_script = f"""
reset;
option solver {solver};
model "{relax_model_file}";
data "{data_file}";
option relax_integrality 1;
# ===== FISSAGGI NODO =====
{fix_block}
# ========================
solve;
display sum{{j in JOBS}} U[j];
"""

    with open(run_file, "w") as f:
        f.write(ampl_script)

    result = subprocess.run([ampl_exe, run_file], capture_output=True, text=True)
    match = re.search(r"sum\{j in JOBS\} U\[j\]\s*=\s*([0-9\.]+)", result.stdout)
    return float(match.group(1)) if match else float("inf")

def append_results_to_csv(
    filename,
    n_jobs,
    r_range,
    p_range,
    tightness,
    bb_tardy,
    bb_time,
    ampl_tardy,
    ampl_time,
    relax_tardy,
    relax_time
):
    import csv
    import os

    file_exists = os.path.isfile(filename)

    with open(filename, mode="a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "n_jobs",
                "r_min", "r_max",
                "p_min", "p_max",
                "tightness",
                "BB_tardy", "BB_time",
                "AMPL_tardy", "AMPL_time",
                "RELAX_tardy", "RELAX_time"
            ])

        writer.writerow([
            n_jobs,
            r_range[0], r_range[1],
            p_range[0], p_range[1],
            tightness,
            bb_tardy, bb_time,
            ampl_tardy, ampl_time,
            relax_tardy, relax_time
        ])


# ---------- MAIN ----------
def main():
    print("== Generazione Job ==")
    n = read_int("\nQuanti job vuoi generare? ", default=20, min_val=1)
    r_min = read_int("Intervallo r: min (default 0): ", default=0)
    r_max = read_int("Intervallo r: max (default 100): ", default=100, min_val=r_min)
    p_min = read_int("Intervallo p: min (default 1): ", default=1, min_val=1)
    p_max = read_int("Intervallo p: max (default 5): ", default=5, min_val=p_min)
    tightness = read_float("Tightness ∈ [0..1+] (default 0.2): ", default=0.2, min_val=0.0)

    generator = JobGenerator(seed=42)
    jobs = generator.generate(n_jobs=n, r_range=(r_min, r_max), p_range=(p_min, p_max), tightness=tightness)

    # ---------------- Stampa e Branch & Bound ----------------
    print("\n== JOB GENERATI ==")
    for job in jobs:
        print(job)

    reset(jobs)
    root = Node()
    start_appr = time.time()
    branch_and_bound(root, jobs, is_on_time_schedulable, select_job)
    end_appr = time.time()
    processing_time_appr = end_appr - start_appr

    best_int, all_T_sets = get_best_solution()
    print(f"\nBest tardy count (B&B): {best_int}")

    # Stampa set ottimi
    if not all_T_sets:
        print("Best tardy set: []")
    elif len(all_T_sets) == 1:
        one = list(all_T_sets[0]) if isinstance(all_T_sets[0], set) else all_T_sets[0]
        print(f"Best tardy set: {sorted(one)}")
    else:
        print(f"All optimal tardy sets ({len(all_T_sets)}): {[sorted(list(s)) for s in all_T_sets]}")

    print(f"\nElapsed time for B&B: {processing_time_appr:.6f}s")
    first_set = all_T_sets[0] if all_T_sets else set()
    stats.print_summary(best_int, first_set)

    # ---------------- Risoluzione AMPL ----------------
    export_to_ampl_dat(jobs)
    model_file = "/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl_model/model.mod"
    relax_model_file = "/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl_model/relax_model.mod"

    start_ampl = time.time()
    ampl_tardy = run_ampl(model_file=model_file, data_file="instance.dat", solver="gurobi")
    end_ampl = time.time()
    processing_time_ampl = end_ampl - start_ampl
    print(f"Elapsed time for AMPL model: {processing_time_ampl:.6f}s")

    start_ampl_relax = time.time()
    ampl_tardy_relax = run_ampl_relax_node(relax_model_file=relax_model_file, T=set(), S=set(), jobs=jobs)
    end_ampl_relax = time.time()
    processing_time_ampl_relax = end_ampl_relax - start_ampl_relax
    print(f"Elapsed time for AMPL relaxed model: {processing_time_ampl_relax:.6f}s")

    # ---------------- Confronto risultati ----------------
    print("\n=== CONFRONTO RISULTATI ===")
    print(f"{'Metodo':<20} {'#Tardy':<10} {'Tempo (s)':<10}")
    print("-" * 45)
    print(f"{'Branch & Bound':<20} {best_int:<10} {processing_time_appr:<10.4f}")
    print(f"{'AMPL Completo':<20} {ampl_tardy:<10} {processing_time_ampl:<10.4f}")
    print(f"{'AMPL Rilassato':<20} {ampl_tardy_relax:<10} {processing_time_ampl_relax:<10.4f}")


    csv_file = os.path.join(
        os.path.dirname(__file__),
        "results_experiments.csv"
    )

    # ---------------- Salvataggio CSV ----------------
    append_results_to_csv(
        filename=csv_file,
        n_jobs=n,
        r_range=(r_min, r_max),
        p_range=(p_min, p_max),
        tightness=tightness,
        bb_tardy=best_int,
        bb_time=processing_time_appr,
        ampl_tardy=ampl_tardy,
        ampl_time=processing_time_ampl,
        relax_tardy=ampl_tardy_relax,
        relax_time=processing_time_ampl_relax
    )

    print(f"\nRisultati salvati in {csv_file}")


if __name__ == "__main__":
    main()
