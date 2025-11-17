import os
import csv
import random
import time
import subprocess

import pandas as pd
import matplotlib.pyplot as plt


from statistics import mean, stdev
from pathlib import Path


# === Parametri sperimentali ===
TIGHTNESS = 0.2
R_RANGE = (0, 100)
P_RANGE = (1, 5)
REPS = 3
N_GRID = (20, 40, 60, 80, 100, 150, 200, 300)

AMPL_EXE = "/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl.linux-intel64/ampl"     
SOLVER = "gurobi"    
MODEL_FILE = "/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl_model/model.mod"

# === Helpers ===

def generate_jobs(n, tightness, r_range, p_range, seed):
    random.seed(seed)
    r = [random.randint(*r_range) for _ in range(n)]
    p = [random.randint(*p_range) for _ in range(n)]
    H = max(r) + sum(p)
    # due date: d_j = r_j + p_j + floor(tightness * (H - (r_j + p_j)))
    d = [r[j] + p[j] + int(tightness * (H - (r[j] + p[j]))) for j in range(n)]
    return r, p, d, H


def edd_heuristic(r, p, d):
    """Euristica EDD con release times."""
    n = len(r)
    done = [False]*n
    t = 0
    C = [0]*n
    remaining = n
    while remaining > 0:
        available = [j for j in range(n) if not done[j] and r[j] <= t]
        if not available:
            t = min([r[j] for j in range(n) if not done[j]], default=t)
            continue
        j_pick = min(available, key=lambda j: (d[j], j))
        start = max(t, r[j_pick])
        finish = start + p[j_pick]
        C[j_pick] = finish
        done[j_pick] = True
        remaining -= 1
        t = finish
    tardy = sum(1 for j in range(n) if C[j] > d[j])
    return tardy


def write_dat(n, r, p, d, H, path):
    with open(path, "w") as f:
        f.write(f"param n := {n};\n")
        f.write(f"param H := {H};\n")
        f.write("param r :=\n")
        for j, val in enumerate(r, 1):
            f.write(f"{j} {val}\n")
        f.write(";\nparam p :=\n")
        for j, val in enumerate(p, 1):
            f.write(f"{j} {val}\n")
        f.write(";\nparam d :=\n")
        for j, val in enumerate(d, 1):
            f.write(f"{j} {val}\n")
        f.write(";\n")


def run_ampl(dat_path):
    run_path = dat_path.replace(".dat", ".run")
    with open(run_path, "w") as f:
        f.write(f"model {MODEL_FILE};\n")
        f.write(f"data {dat_path};\n")
        f.write(f"option solver {SOLVER};\n")
        f.write("solve;\n")
        f.write("display TotalTardy;\n")

    t0 = time.time()
    proc = subprocess.run([AMPL_EXE, run_path], capture_output=True, text=True)
    t1 = time.time()

    opt_tardy = None
    for line in proc.stdout.splitlines():
        if "TotalTardy" in line and "=" in line:
            try:
                opt_tardy = int(float(line.split("=")[-1].strip()))
                break
            except ValueError:
                pass
    runtime = t1 - t0
    return opt_tardy, runtime, proc.stdout


def write_csv(rows, path):
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def print_summary(rows, key="n"):
    print("\n-- SUMMARY --")
    groups = {}
    for r in rows:
        groups.setdefault(r[key], []).append(r)

    for g in sorted(groups.keys()):
        gr = groups[g]
        def ms(vals): return f"{mean(vals):.3f} ± {stdev(vals):.3f}" if len(vals) > 1 else f"{vals[0]:.3f} ± 0.000"
        opt = [r["opt_tardy"] for r in gr if r["opt_tardy"] is not None]
        gap = [r["gap"] for r in gr if r["gap"] is not None]
        rt = [r["runtime_s"] for r in gr]
        print(f"n={g:3d}: opt={ms(opt)}  gap={ms(gap)}  time={ms(rt)}")
    print("-- end summary --\n")


# === Main experiment ===

def experiment_scaling_n():
    Path("results").mkdir(exist_ok=True)
    Path("instances").mkdir(exist_ok=True)
    out_csv = "results/results_scaling_ampl.csv"

    rows = []
    print(f"== Esperimento scaling su n (tightness={TIGHTNESS}) ==")
    for n in N_GRID:
        for rep in range(REPS):
            seed = 1000 * n + rep
            r, p, d, H = generate_jobs(n, TIGHTNESS, R_RANGE, P_RANGE, seed)
            ub_heur = edd_heuristic(r, p, d)
            dat_file = f"instances/inst_n{n}_rep{rep}.dat"
            write_dat(n, r, p, d, H, dat_file)

            opt_tardy, runtime, _ = run_ampl(dat_file)
            gap = (ub_heur - opt_tardy) if (opt_tardy is not None) else None

            rows.append({
                "n": n,
                "rep": rep,
                "seed": seed,
                "opt_tardy": opt_tardy,
                "ub_heur": ub_heur,
                "gap": gap,
                "runtime_s": runtime,
                "tightness": TIGHTNESS,
            })

            print(f"n={n:3d} rep={rep}  opt={opt_tardy}  ub={ub_heur}  gap={gap}  time={runtime:.3f}s")

    write_csv(rows, out_csv)
    print_summary(rows, key="n")
    print(f"[OK] CSV salvato in {out_csv}")
        # === Grafici automatici ===
    df = pd.read_csv(out_csv)
    os.makedirs("plots", exist_ok=True)
    plot_runtime_vs_n(df, "plots/runtime_vs_n_ampl.png")
    plot_gap_vs_n(df, "plots/gap_vs_n_ampl.png")
    print(f"[DONE] Grafici salvati in cartella plots/")



def agg_mean_std(df: pd.DataFrame, by: str, cols: list[str]) -> pd.DataFrame:
    g = df.groupby(by)[cols].agg(['mean', 'std']).reset_index()
    g.columns = [f"{c[0]}_{c[1]}" if c[1] else c[0] for c in g.columns.values]
    return g

def plot_runtime_vs_n(df: pd.DataFrame, out_path: str):
    g = agg_mean_std(df, by='n', cols=['runtime_s'])
    x, y, e = g['n'], g['runtime_s_mean'], g['runtime_s_std']
    plt.figure()
    plt.errorbar(x, y, yerr=e, fmt='-o', capsize=4)
    plt.yscale('log')
    plt.xlabel('n (numero job)')
    plt.ylabel('Runtime medio [s] (log)')
    plt.title('Tempo di esecuzione vs n (AMPL)')
    plt.grid(True, which='both', linestyle=':')
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
    print(f"[OK] Salvato grafico: {out_path}")

def plot_gap_vs_n(df: pd.DataFrame, out_path: str):
    g = agg_mean_std(df, by='n', cols=['gap'])
    x, y, e = g['n'], g['gap_mean'], g['gap_std']
    plt.figure()
    plt.errorbar(x, y, yerr=e, fmt='-o', capsize=4)
    plt.xlabel('n (numero job)')
    plt.ylabel('Gap medio (UB - Opt)')
    plt.title('Gap euristica (EDD) vs n (AMPL)')
    plt.grid(True, linestyle=':')
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
    print(f"[OK] Salvato grafico: {out_path}")



if __name__ == "__main__":
    experiment_scaling_n()
