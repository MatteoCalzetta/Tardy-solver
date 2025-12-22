from pathlib import Path
import re
import subprocess
import time

# ---------------- PATH ----------------
DATA_DIR = Path("/home/giulia/Documenti/AMOD_project/Tardy-solver/")
DAT_FILE = DATA_DIR / "instance.dat"
MODEL_EXACT = Path("/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl_model/model.mod")
MODEL_RELAX = Path("/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl_model/relax_model.mod")
AMPL_EXE = "/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl.linux-intel64/ampl"

# ---------------- UTIL ----------------
def run_ampl(model_file, datfile):
    """Esegue AMPL e ritorna il valore totale di tardy."""
    run_file = "run_ampl_test.run"
    script = f"""
reset;
option solver gurobi;
model "{model_file}";
data "{datfile}";
solve;
display sum{{j in JOBS}} U[j];
"""
    with open(run_file, "w") as f:
        f.write(script)

    t0 = time.time()
    proc = subprocess.run([AMPL_EXE, run_file], capture_output=True, text=True)
    t1 = time.time()

    elapsed = t1 - t0
    output = proc.stdout

    match = re.search(r"sum\{j in JOBS\} U\[j\]\s*=\s*([0-9]+)", output)
    if match:
        tardy_count = int(match.group(1))
        return tardy_count, elapsed
    else:
        raise ValueError(f"Impossibile leggere il risultato AMPL:\n{output}")

# ---------------- TEST ----------------
def test_ampl_vs_ub(dat_file, model_exact, model_relax, ub):
    """Confronta AMPL completo e rilassato con l'UB."""
    # Risolvo modello completo
    opt, t_exact = run_ampl(model_exact, dat_file)
    print(f"AMPL completo: {opt} tardy in {t_exact:.2f}s")

    # Risolvo modello rilassato
    lb, t_relax = run_ampl(model_relax, dat_file)
    print(f"AMPL rilassato: {lb} tardy in {t_relax:.2f}s")

    # Confronti
    assert lb <= opt, f"LB {lb} > OPT {opt}"
    assert opt <= ub, f"OPT {opt} > UB {ub}"

    gap = (ub - lb) / ub if ub > 0 else 0
    print(f"Gap rispetto UB: {100*gap:.2f}%")

# ---------------- MAIN TEST ----------------
if __name__ == "__main__":
    # Qui metti l'UB già calcolata dal main
    heuristic_ub = 3  # esempio, sostituire con il valore reale del main

    test_ampl_vs_ub(DAT_FILE, MODEL_EXACT, MODEL_RELAX, heuristic_ub)
