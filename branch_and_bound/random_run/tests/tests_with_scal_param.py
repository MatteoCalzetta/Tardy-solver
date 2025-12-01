import os
import sys
import time
import csv
from statistics import mean, stdev

# === Tightness fissa per tutti gli esperimenti ===
TIGHTNESS = 0.2

# Path: sali di due livelli fino alla cartella che contiene bb.py, node.py, job_generator.py, util.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from bb import reset, branch_and_bound, get_best_solution, stats, heuristic_upper_bound
from node import Node
from job_generator import JobGenerator
from util import is_on_time_schedulable, select_job
import lower_bound.lower_bound as lbmod  # per ablation dei LB


class LBMode:
    """
    Context manager per cambiare il tipo di LB usato.
    Cambia lower_bound.lower_bound.LB_MODE per la durata del 'with'.
    """
    def __init__(self, mode: str):
        import lower_bound.lower_bound as lb_mod
        self.lb_mod = lb_mod
        self.prev_mode = getattr(lb_mod, "LB_MODE", "combined")
        self.new_mode = mode

    def __enter__(self):
        self.lb_mod.LB_MODE = self.new_mode
        return self

    def __exit__(self, exc_type, exc, tb):
        self.lb_mod.LB_MODE = self.prev_mode


# ---------------------------
# Helpers: metrics
# ---------------------------

def _collect_metrics(jobs, run_name=""):
    """
    Esegue 1 run di B&B e ritorna un dict con metriche essenziali:
    - opt_tardy, ub_heur, gap
    - nodes, depth_avg
    - lb_calls, lb_time_s
    - fathom_lb, fathom_leaf
    - runtime_s
    - hit_node_limit (True se abbiamo superato MAX_NODES in bb.py)
    """
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

    hit_limit = bool(getattr(stats, "hit_node_limit", False))

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
        "hit_node_limit": hit_limit,
    }


# ---------------------------
# Generazione istanze
# ---------------------------

def make_jobs(n, mode="tight", r_range=(0, 100), p_range=(1, 5), seed=42):
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
    n_grid=(5, 10, 15, 20, 25, 30),
    reps=5,
    mode="tight",
    r_range=(0, 100),
    p_range=(1, 5),
    out_csv="results_scaling_n.csv",
):
    """
    Scaling su n con LB di Lawler (overload + knapsack) e tightness fissa.
    Registra anche se il run è stato troncato per limite di nodi.
    """
    rows = []
    print(f"== SCALING su n (tightness fissa = {TIGHTNESS}) ==")
    for n in n_grid:
        for r in range(reps):
            seed = 1000 * n + r
            jobs = make_jobs(n, mode=mode, r_range=r_range, p_range=p_range, seed=seed)
            m = _collect_metrics(jobs, run_name=f"n={n}-rep={r}")
            rows.append(m)
            trunc = " TRUNC" if m["hit_node_limit"] else ""
            print(
                f"n={n:3d} rep={r}  opt={m['opt_tardy']:3d} ub={m['ub_heur']:3d} "
                f"gap={m['gap']:3d} nodes={m['nodes']:7d} time={m['runtime_s']:.3f}s{trunc}"
            )

    _write_csv(rows, out_csv)
    _print_summary(rows, key="n")
    print(f"[OK] CSV salvato in {out_csv}")


# -----------------------------------------
# Esperimento 2: Ablation dei lower bounds
# -----------------------------------------

class LBMode:
    """
    Context manager per variare il tipo di LB usato nel B&B
    via monkeypatch su lower_bound.lower_bound.compute_lb_combined.

    mode:
      - "combined"       : overload + knapsack (default del B&B)
      - "overload_only"  : solo overload intervals
      - "no_LB"          : sempre 0 (nessun bound)
    """
    def init(self, mode: str):
        self.mode = mode
        self._orig = lbmod.compute_lb_combined
    def enter(self):
        if self.mode == "overload_only":
            def _lb_over(jobs):
                return lbmod.compute_lb_overload_intervals(jobs)
            lbmod.compute_lb_combined = _lb_over
        elif self.mode == "no_LB":
            def _lb_zero(jobs):
                return 0
            lbmod.compute_lb_combined = _lb_zero
        elif self.mode == "combined":
            # tieni la definizione originale
            lbmod.compute_lb_combined = self._orig
        return self

    def exit(self, exc_type, exc, tb):
        lbmod.compute_lb_combined = self._orig


def experiment_lb_ablation(
    n=80,
    reps=3,
    mode="tight",
    r_range=(0,100),
    p_range=(1,5),
    out_csv="results_lb_ablation.csv",
):

    rows = []
    print(f"== ABLATION dei lower bound (tightness fissa = {TIGHTNESS}) ==")

    def _runs(label, lb_mode: str):
        for r in range(reps):
            seed = 3000 + r
            jobs = make_jobs(n, mode=mode, r_range=r_range, p_range=p_range, seed=seed)
            with LBMode(lb_mode):
                m = _collect_metrics(jobs, run_name=f"{label}-rep={r}")
            m["config"] = label
            rows.append(m)
            print(f"{label:14s} rep={r}  opt={m['opt_tardy']:3d} ub={m['ub_heur']:3d} "
                  f"gap={m['gap']:3d} nodes={m['nodes']:7d} time={m['runtime_s']:.3f}s")

    # qui scegli la modalità da passare al B&B
    _runs("overload_only", "overload_only")
    _runs("knap_only",     "knap_only")
    _runs("combined",      "combined")

    _write_csv(rows, out_csv)
    _print_summary(rows, key="config")
    print(f"[OK] CSV salvato in {out_csv}")


# ---------------
# Utility interne
# ---------------

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
        truncs = [int(r["hit_node_limit"]) for r in gr]
        print(
            f"{key}={gk}:  opt={_m_s(opt)}  gap={_m_s(gap)}  nodes={_m_s(nodes)}  "
            f"time={_m_s(rt)}  lb_time={_m_s(lbtime)}  "
            f"trunc_rate={sum(truncs)}/{len(truncs)}"
        )
    print("-- end summary --\n")


# ---------------
# Main launcher
# ---------------

if __name__ == "__main__":
    outdir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(outdir, exist_ok=True)

    # 1) Scaling su n (tightness fissa)
    experiment_scaling_n(
        n_grid=(5, 10, 15, 20, 25, 30),
        reps=5,
        out_csv=os.path.join(outdir, "results_scaling_n.csv"),
    )

    # 2) Ablation dei LB (tightness fissa, n fisso)
    experiment_lb_ablation(
        n=80,
        reps=5,
        out_csv=os.path.join(outdir, "results_lb_ablation.csv"),
    )

    print(f"Tutti i CSV sono in: {outdir}")
