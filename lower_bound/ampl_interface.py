# lower_bound/ampl_interface.py (o dove hai la funzione)

import re
import subprocess
import math

def run_ampl_relax_node(relax_model_file, T, S, jobs, data_file="instance.dat", solver="gurobi"):
    """
    Risolve il modello rilassato con AMPL fissando le variabili dei job
    già decisi in T (tardy) e S (on-time).
    Restituisce il lower bound intero (ceil della soluzione LP).
    """

    ampl_exe = "/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl.linux-intel64/ampl"
    run_file = "run_ampl_relax_node.run"

    fix_cmds = []

    # Fissa i job tardy
    for j in T:
        t = jobs[j-1].d + jobs[j-1].p  # tempo tardivo qualsiasi
        fix_cmds.append(f"fix x[{j},{t}] := 1;")
        fix_cmds.append(f"for {{t2 in 0..H: t2 != {t}}} fix x[{j},t2] := 0;")
        fix_cmds.append(f"fix U[{j}] := 1;")

    # Fissa i job on-time
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

    # Scrivi lo script AMPL
    with open(run_file, "w") as f:
        f.write(ampl_script)

    # Esegui AMPL
    result = subprocess.run([ampl_exe, run_file],
                            capture_output=True,
                            text=True)

    # Estrai il valore LP
    match = re.search(r"sum\{j in JOBS\} U\[j\]\s*=\s*([0-9\.]+)", result.stdout)
    if match:
        lb_lp_float = float(match.group(1))
        lb_lp_int = math.ceil(lb_lp_float)  # converti in intero per pruning
        return lb_lp_int
    else:
        # se errore, restituisci valore conservativo alto
        return float("inf")
