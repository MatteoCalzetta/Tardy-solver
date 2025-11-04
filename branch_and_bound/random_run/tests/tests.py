import re
import sys
import os
import time
import subprocess

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from bb import reset, branch_and_bound, get_best_solution, stats, heuristic_upper_bound
from util import is_on_time_schedulable, select_job
from node import Node
from job import Job

def _fmt_sets(sets, k=3):
    if not sets:
        return "[]"
    view = [sorted(list(s)) for s in sets[:k]]
    more = "" if len(sets) <= k else f" ... (+{len(sets)-k} altre)"
    return f"{view}{more}"

def run_test(jobs, expected_opt=None, name=""):
    # UB euristico esplicito
    ub_heur, T_heur = heuristic_upper_bound(jobs)

    # B&B
    reset(jobs)   # azzera best/stats
    root = Node()
    t0 = time.time()
    branch_and_bound(root, jobs, is_on_time_schedulable, select_job)
    t1 = time.time()

    opt, all_T = get_best_solution()
    all_T = all_T or []
    gap = None if opt is None else (ub_heur - opt)
    ok_opt = (expected_opt is None) or (opt == expected_opt)
    ok_gap = (opt is None) or (ub_heur >= opt)  # UB deve sovrastimare
    ok = ok_opt and ok_gap

    check = "✅ PASS" if ok else "❌ FAIL"
    exp_str = "n/a" if expected_opt is None else str(expected_opt)

    print(f"\n[{name}] {check}")
    print(f"  • Expected optimum       : {exp_str}")
    print(f"  • B&B optimum            : {opt}")
    print(f"  • Heuristic UB (EDD)     : {ub_heur}  (gap = {gap})  [{ 'OK' if ok_gap else 'BAD' }]")
    print(f"  • # optimal tardy sets   : {len(all_T)}")
    print(f"  • EDD tardy set (preview): {sorted(list(T_heur))}")
    print(f"  • Optimal sets (preview) : {_fmt_sets(all_T, k=3)}")
    print(f"  • Nodes explored         : {getattr(stats, 'nodi_generati', 0)}")
    nd = getattr(stats, 'nodi_generati', 0)
    depth_avg = (getattr(stats, 'profondità_totale', 0) / nd) if nd else 0.0
    print(f"  • Avg depth              : {depth_avg:.2f}")
    print(f"  • LB calls / time (s)    : {getattr(stats, 'chiamate_lb', 0)} / {getattr(stats, 'tempo_totale_lb', 0.0):.6f}")
    print(f"  • Fathom by LB / leaf    : {getattr(stats, 'fathom_lb', 0)} / {getattr(stats, 'fathom_leaf', 0)}")
    print(f"  • Runtime (s)            : {t1 - t0:.6f}")

    stats.print_summary(opt, (all_T[0] if all_T else set()))
    return ok

# --- istanze piccole ---

def test_all_on_time():
    # d_j = cumulative sum => ottimo = 0
    P = [2,1,3,2,2]
    R = [0]*len(P)
    D, s = [], 0
    for p in P:
        s += p; D.append(s)
    jobs = [Job(i+1,R[i],P[i],D[i]) for i in range(len(P))]
    return run_test(jobs, expected_opt=0, name="all_on_time")

def test_one_tardy():
    R = [0,0,0]; P = [5,5,5]; D = [5,9,10]
    jobs = [Job(i+1,R[i],P[i],D[i]) for i in range(3)]
    return run_test(jobs, expected_opt=1, name="one_tardy")

def test_k_tardy_block(n=10, m=7):
    # n job, p=1, r=0, d=m  => ottimo = n-m
    jobs = [Job(i+1,0,1,m) for i in range(n)]
    return run_test(jobs, expected_opt=n-m, name=f"k_tardy_block(n={n},m={m})")

def test_release_forced():
    R = [0,0,8]; P = [4,4,3]; D = [7,8,10]
    jobs = [Job(i+1,R[i],P[i],D[i]) for i in range(3)]
    return run_test(jobs, expected_opt=1, name="release_forced")

def test_symmetry_many_opt():
    # 5 job, r=0, p=1, d=3 => ottimo = 2, molte soluzioni ottime
    jobs = [Job(i+1,0,1,3) for i in range(5)]
    return run_test(jobs, expected_opt=2, name="symmetry_many_opt")


if __name__ == "__main__":
    print("== Running basic validation tests ==\n", flush=True)

    suite = [
        ("all_on_time",         test_all_on_time),
        ("one_tardy",           test_one_tardy),
        ("k_tardy_block(10,7)", lambda: test_k_tardy_block(10, 7)),
        ("release_forced",      test_release_forced),
        ("symmetry_many_opt",   test_symmetry_many_opt),
    ]

    n_pass = 0
    n_fail = 0

    for name, fn in suite:
        try:
            ok = fn()
        except Exception as e:
            ok = False
            print(f"[{name}] 💥 EXCEPTION: {e}", flush=True)
        if ok:
            n_pass += 1
        else:
            n_fail += 1

    total = n_pass + n_fail
    print(f"\n==== SUMMARY: {n_pass} PASS, {n_fail} FAIL, total {total} ====", flush=True)

    # exit code utile per CI
    import sys as _sys
    _sys.exit(0 if n_fail == 0 else 1)
