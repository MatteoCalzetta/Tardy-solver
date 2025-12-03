import sys
import os
import time

# Aggiusta il path al progetto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../branch_and_bound/')))

from bb import reset, branch_and_bound, get_best_solution, stats, heuristic_upper_bound
from util import is_on_time_schedulable, select_job
from node import Node
from job import Job
from lower_bound.lower_bound import compute_lb_moore


def _fmt_sets(sets, k=3):
    """Formato carino per stampare i primi k set ottimi."""
    if not sets:
        return "[]"
    view = [sorted(list(s)) for s in sets[:k]]
    more = "" if len(sets) <= k else f" ... (+{len(sets)-k} altre)"
    return f"{view}{more}"


def run_test(jobs, expected_opt=None, name=""):
    # 1) UB euristico esplicito (non-preemptive EDD)
    ub_heur, T_heur = heuristic_upper_bound(jobs)

    # 2) LB Moore sull'istanza intera (rilassata)
    lb_moore = compute_lb_moore(jobs)

    # 3) B&B vero e proprio
    reset(jobs)  # azzera best/stats globali
    root = Node()

    t0 = time.time()
    branch_and_bound(root, jobs, is_on_time_schedulable, select_job)
    t1 = time.time()

    opt, all_T = get_best_solution()
    all_T = all_T or []

    # 4) Verifiche di coerenza
    gap = None if opt is None else (ub_heur - opt)

    ok_opt = (expected_opt is None) or (opt == expected_opt)
    # UB deve essere >= ottimo (sovrastima o uguale)
    ok_ub = (opt is None) or (ub_heur >= opt)
    # LB di Moore deve essere <= ottimo (sottostima o uguale)
    ok_lb = (opt is None) or (lb_moore <= opt)

    ok = ok_opt and ok_ub and ok_lb

    check = "✅ PASS" if ok else "❌ FAIL"
    exp_str = "n/a" if expected_opt is None else str(expected_opt)

    print(f"\n[{name}] {check}")
    print(f" • Expected optimum        : {exp_str}")
    print(f" • B&B optimum             : {opt}")
    print(f" • Heuristic UB (EDD)      : {ub_heur} (gap = {gap}) [{'OK' if ok_ub else 'BAD'}]")
    print(f" • Moore LB (rilassato)    : {lb_moore} [{'OK' if ok_lb else 'BAD'}]")
    print(f" • # optimal tardy sets    : {len(all_T)}")
    print(f" • EDD tardy set (preview) : {sorted(list(T_heur))}")
    print(f" • Optimal sets (preview)  : {_fmt_sets(all_T, k=3)}")

    # Statistiche B&B
    nd = getattr(stats, 'nodi_generati', 0)
    depth_avg = (getattr(stats, 'profondità_totale', 0) / nd) if nd else 0.0

    print(f" • Nodes explored          : {nd}")
    print(f" • Avg depth               : {depth_avg:.2f}")
    print(f" • LB calls / time (s)     : {getattr(stats, 'chiamate_lb', 0)} / "
          f"{getattr(stats, 'tempo_totale_lb', 0.0):.6f}")
    print(f" • Fathom by LB / leaf     : {getattr(stats, 'fathom_lb', 0)} / "
          f"{getattr(stats, 'fathom_leaf', 0)}")
    print(f" • Runtime (s)             : {t1 - t0:.6f}")

    # Riassunto compatibile con la funzione di stampa delle stats
    stats.print_summary(opt, (all_T[0] if all_T else set()))

    return ok


# --- istanze piccole classiche ---

def test_all_on_time():
    """
    d_j = somma cumulata dei p_j con r_j = 0
    -> esiste una schedula che completa esattamente al limite: nessun tardy, ottimo = 0.
    Moore vede la stessa cosa (nessuna ragione per scartare job).
    """
    P = [2, 1, 3, 2, 2]
    R = [0] * len(P)
    D = []
    s = 0
    for p in P:
        s += p
        D.append(s)
    jobs = [Job(i+1, R[i], P[i], D[i]) for i in range(len(P))]
    return run_test(jobs, expected_opt=0, name="all_on_time")


def test_one_tardy():
    """
    Tre job tutti disponibili a 0, p = 5,5,5 e due-date [5,9,10].
    - Non-preemptive: con EDD si riesce a mettere on-time solo uno (o due a seconda della combinazione),
      ottimo = 1 tardy.
    - Moore lavora nello stesso scenario (niente release), quindi LB = 1.
    """
    R = [0, 0, 0]
    P = [5, 5, 5]
    D = [5, 9, 10]
    jobs = [Job(i+1, R[i], P[i], D[i]) for i in range(3)]
    return run_test(jobs, expected_opt=1, name="one_tardy")


def test_k_tardy_block(n=10, m=7):
    """
    n job tutti con:
      - r = 0
      - p = 1
      - d = m

    In totale serve tempo n, ma la deadline comune è m:
      -> al massimo si completano on-time m job
      -> ottimo = n - m tardy.

    Moore vede esattamente lo stesso problema (1 || sum U_j con scadenza uguale per tutti),
    quindi LB = n - m.
    """
    jobs = [Job(i+1, 0, 1, m) for i in range(n)]
    return run_test(jobs, expected_opt=n-m, name=f"k_tardy_block(n={n},m={m})")


def test_release_forced():
    """
    Esempio con release che 'forzano' il ritardo di almeno un job.

    R = [0, 0, 8]
    P = [4, 4, 3]
    D = [7, 8, 10]

    - Con release:
        i primi due job possono partire da 0 e occupare [0,8].
        Il terzo job arriva a 8 e ha d=10, ci sta per poco: con una schedula adatta
        si ottiene un solo tardy (ottimo = 1).

    - Nel rilassamento Moore:
        si prende r_min = 0 e si ignora il fatto che il terzo ha r=8,
        ma in questo caso l'ottimo rilassato coincide con l'ottimo reale (LB = 1).
    """
    R = [0, 0, 8]
    P = [4, 4, 3]
    D = [7, 8, 10]
    jobs = [Job(i+1, R[i], P[i], D[i]) for i in range(3)]
    return run_test(jobs, expected_opt=1, name="release_forced")


def test_symmetry_many_opt():
    """
    5 job identici con:
      - r = 0
      - p = 1
      - d = 3

    In 3 unità di tempo se ne possono completare al massimo 3 on-time:
      -> ottimo = 2 tardy.

    La struttura simmetrica fa sì che ci siano molte soluzioni ottime diverse
    (qualsiasi scelta di 3 job on-time).

    Moore vede lo stesso problema e restituisce LB = 2.
    """
    jobs = [Job(i+1, 0, 1, 3) for i in range(5)]
    return run_test(jobs, expected_opt=2, name="symmetry_many_opt")


# --- test extra mirati per vedere LB < OPT (rilassamento che regala troppo) ---

def test_moore_strict_lb():
    """
    Costruisce un caso in cui il rilassamento alla Moore è più 'ottimista'
    del problema con release.

    Idea:
      - il rilassamento ignora le release individuali (le schiaccia tutte a r_min),
        quindi può mettere job più 'strettamente' uno dopo l'altro.
      - con le release reali, qualche job parte più tardi e non riesce a finire in tempo.

    Esempio semplice:

      J1: r=0, p=3, d=4
      J2: r=3, p=3, d=6

    Nel rilassamento:
      r_min = 0
      d_eff1 = 4, d_eff2 = 6
      Sequenza EDD: [J1, J2]
      t = 3 (J1), t = 6 (J2) -> nessun tardy => LB_Moore = 0

    Con le release reali:
      J1 da 0 a 3, J2 può iniziare solo a 3, finisce a 6, ancora in tempo,
      quindi qui OPT = 0 (quindi LB = OPT).

    Se questo non crea il gap, si può variare i numeri; comunque il test
    verifica che LB_Moore <= OPT rimane vero anche con release non banali.
    """
    R = [0, 3]
    P = [3, 3]
    D = [4, 6]
    jobs = [Job(i+1, R[i], P[i], D[i]) for i in range(2)]
    # qui l'ottimo è 0 (tutti on-time), Moore deve dare LB <= 0 (cioè 0)
    return run_test(jobs, expected_opt=0, name="moore_strict_lb")


if __name__ == "__main__":
    print("== Running basic validation tests ==\n", flush=True)

    suite = [
        ("all_on_time", test_all_on_time),
        ("one_tardy", test_one_tardy),
        ("k_tardy_block(10,7)", lambda: test_k_tardy_block(10, 7)),
        ("release_forced", test_release_forced),
        ("symmetry_many_opt", test_symmetry_many_opt),
        ("moore_strict_lb", test_moore_strict_lb),
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

    import sys as _sys
    _sys.exit(0 if n_fail == 0 else 1)
