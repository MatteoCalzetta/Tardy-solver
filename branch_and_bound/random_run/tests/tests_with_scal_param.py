import os
import sys
import time
import csv
from statistics import mean, stdev

# === Tightness fissa per tutti gli esperimenti ===
TIGHTNESS = 0.2

# Assicurati che il path punti alla cartella che contiene bb.py, node.py, job_generator.py, util.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from bb import reset, branch_and_bound, get_best_solution, stats, heuristic_upper_bound
from node import Node
from job_generator import JobGenerator
from util import is_on_time_schedulable, select_job

# ---------------------------
# Helpers: metrics + patch LB
# ---------------------------

def _collect_metrics(jobs, run_name=""):
    """Esegue 1 run di B&B, ritorna dict con metriche essenziali."""
    ub_heur, _ = heuristic_upper_bound(jobs)

    reset(jobs)
    root = Node()
    t0 = time.time()
    branch_and_bound(root, jobs, is_on_time_schedulable, select_job)
    t1 = time.time()

    opt, _all_T = get_best_solution()
    gap = ub_heur - opt if (opt is not None) else None

    nd = getattr(stats, 'nodi_generati', 0)
    dep_avg = (getattr(stats, 'profondità_totale', 0) / nd) if nd else 0.0

    return {
        "run": run_name,
        "n": len(jobs),
        "opt_tardy": opt,
        "ub_heur": ub_heur,
        "gap": gap,
        "nodes": nd,
        "depth_avg": dep_avg,
        "lb_calls": getattr(stats, 'chiamate_lb', 0),
        "lb_time_s": getattr(stats, 'tempo_totale_lb', 0.0),
        "fathom_lb": getattr(stats, 'fathom_lb', 0),
        "fathom_leaf": getattr(stats, 'fathom_leaf', 0),
        "runtime_s": (t1 - t0),
        "tightness": TIGHTNESS,
    }

class KnapsackToggle:
    """Abilita/Disabilita knapsack senza toccare il codice di bb.py."""
    def __init__(self, enable: bool):
        self.enable = enable
        import bb as _bb
        self._bb = _bb
        self.prev_n = getattr(_bb, "KP_N_MAX", None)
        self.prev_h = getattr(_bb, "KP_H_MAX", None)

    def __enter__(self):
        if self.prev_n is None or self.prev_h is None:
            return
        if not self.enable:
            self._bb.KP_N_MAX = -1
            self._bb.KP_H_MAX = -1

    def __exit__(self, exc_type, exc, tb):
        if self.prev_n is not None:
            self._bb.KP_N_MAX = self.prev_n
        if self.prev_h is not None:
            self._bb.KP_H_MAX = self.prev_h

class NoLBPatch:
    """Azzera qualunque LB (Node.compute_lb -> 0) per configurazione 'no_LB'."""
    def __init__(self):
        self.orig = getattr(Node, "compute_lb", None)

    def __enter__(self):
        def _noop_compute_lb(self_node, jobs_remain):
            self_node.lb = 0
        Node.compute_lb = _noop_compute_lb

    def __exit__(self, exc_type, exc, tb):
        if self.orig is not None:
            Node.compute_lb = self.orig

# ---------------------------
# Generazione istanze
# ---------------------------

def make_jobs(n, mode="tight", r_range=(0,100), p_range=(1,5), seed=42):
    gen = JobGenerator(seed=seed)
    return gen.generate(
        n_jobs=n,
        r_range=r_range,
        p_range=p_range,
        tightness=TIGHTNESS,   # <- tightness fissa qui
        mode=mode,
    )

# ---------------------------
# Esperimento 1: Scaling su n
# ---------------------------

def experiment_scaling_n(
    n_grid=(20, 40, 60, 80, 100, 150, 200, 300),
    reps=5,
    mode="tight",
    r_range=(0,100),
    p_range=(1,5),
    out_csv="results_scaling_n.csv",
):
    rows = []
    print(f"== SCALING su n (tightness fissa = {TIGHTNESS}) ==")
    for n in n_grid:
        for r in range(reps):
            seed = 1000*n + r
            jobs = make_jobs(n, mode=mode, r_range=r_range, p_range=p_range, seed=seed)
            m = _collect_metrics(jobs, run_name=f"n={n}-rep={r}")
            rows.append(m)
            print(f"n={n:3d} rep={r}  opt={m['opt_tardy']:3d} ub={m['ub_heur']:3d} gap={m['gap']:3d} "
                  f"nodes={m['nodes']:7d} time={m['runtime_s']:.3f}s")
    _write_csv(rows, out_csv)
    _print_summary(rows, key="n")
    print(f"[OK] CSV salvato in {out_csv}")

# -----------------------------------------
# Esperimento 2: Ablation dei lower bounds
# -----------------------------------------

def experiment_lb_ablation(
    n=80,
    reps=5,
    mode="tight",
    r_range=(0,100),
    p_range=(1,5),
    out_csv="results_lb_ablation.csv",
):
    """
    Tre configurazioni:
      A) solo PEDD (knapsack OFF)
      B) PEDD + knapsack (ON)
      C) no-LB (compute_lb -> 0)
    """
    rows = []
    print(f"== ABLATION dei lower bound (tightness fissa = {TIGHTNESS}) ==")

    def _runs(label, context_managers):
        for r in range(reps):
            seed = 3000 + r
            jobs = make_jobs(n, mode=mode, r_range=r_range, p_range=p_range, seed=seed)
            with _chain(context_managers):
                m = _collect_metrics(jobs, run_name=f"{label}-rep={r}")
            m["config"] = label
            rows.append(m)
            print(f"{label:14s} rep={r}  opt={m['opt_tardy']:3d} ub={m['ub_heur']:3d} gap={m['gap']:3d} "
                  f"nodes={m['nodes']:7d} time={m['runtime_s']:.3f}s")

    # A) solo PEDD: knapsack OFF
    _runs("PEDD_only", [KnapsackToggle(enable=False)])

    # B) PEDD + knapsack
    _runs("PEDD+KP", [KnapsackToggle(enable=True)])

    # C) no-LB: azzera anche PEDD
    _runs("no_LB", [NoLBPatch(), KnapsackToggle(enable=False)])

    _write_csv(rows, out_csv)
    _print_summary(rows, key="config")
    print(f"[OK] CSV salvato in {out_csv}")

# ---------------
# Utility interne
# ---------------

class _chain:
    """Permette 'with' annidati in una sola riga: with _chain([cm1, cm2, ...])"""
    def __init__(self, cms):
        self.cms = cms
        self._exited = []

    def __enter__(self):
        for cm in self.cms:
            cm.__enter__()
            self._exited.append(cm)
        return self

    def __exit__(self, exc_type, exc, tb):
        while self._exited:
            cm = self._exited.pop()
            cm.__exit__(exc_type, exc, tb)

def _write_csv(rows, path):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def _print_summary(rows, key):
    """
    Stampa medie/σ per gruppi (key='n' o 'config').
    """
    print("\n-- SUMMARY (mean ± std) per", key, "--")
    groups = {}
    for r in rows:
        groups.setdefault(r[key], []).append(r)

    def _m_s(vals):
        if len(vals) == 1:
            return f"{vals[0]:.3f} ± 0.000"
        return f"{mean(vals):.3f} ± {stdev(vals):.3f}"

    for gk in sorted(groups, key=lambda x: (str(x))):
        gr = groups[gk]
        opt = [r["opt_tardy"] for r in gr]
        gap = [r["gap"] for r in gr]
        nodes = [r["nodes"] for r in gr]
        rt = [r["runtime_s"] for r in gr]
        lbtime = [r["lb_time_s"] for r in gr]
        print(f"{key}={gk}:  opt={_m_s(opt)}  gap={_m_s(gap)}  nodes={_m_s(nodes)}  "
              f"time={_m_s(rt)}  lb_time={_m_s(lbtime)}")
    print("-- end summary --\n")

# ---------------
# Main launcher
# ---------------

if __name__ == "__main__":
    outdir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(outdir, exist_ok=True)

    # 1) Scaling su n (tightness fissa)
    experiment_scaling_n(
        n_grid=(20, 40, 60, 80, 100, 150, 200, 300),
        reps=3,
        out_csv=os.path.join(outdir, "results_scaling_n.csv"),
    )

    # 2) Ablation dei LB (tightness fissa)
    experiment_lb_ablation(
        n=80,
        reps=3,
        out_csv=os.path.join(outdir, "results_lb_ablation.csv"),
    )

    print(f"Tutti i CSV sono in: {outdir}")
