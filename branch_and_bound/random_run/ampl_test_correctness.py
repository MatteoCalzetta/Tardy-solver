import os
import sys
import time

# --- Imposta la root del progetto ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# --- Import dei moduli dal branch_and_bound ---
from job_generator import JobGenerator
from node import Node
from bb import branch_and_bound, get_best_solution, reset
from util import is_on_time_schedulable, select_job

# --- Import delle funzioni di main_random.py ---
from branch_and_bound.random_run.main_random import (
    export_to_ampl_dat,
    run_ampl,
    run_ampl_relax_node,
)


class AMPLCorrectnessTest:
    """
    Test automatico di correttezza del modello AMPL
    confrontando OPT_AMPL con OPT_BB.
    """

    def __init__(
        self,
        model_file,
        relax_model_file,
        solver="gurobi",
        workdir=".",
    ):
        self.model_file = model_file
        self.relax_model_file = relax_model_file
        self.solver = solver
        self.workdir = workdir

    # ---------------------------
    # Core solver per 1 istanza
    # ---------------------------
    def solve_instance(self, jobs):
        # --- Branch & Bound ---
        reset(jobs)
        root = Node()
        t0 = time.time()
        branch_and_bound(root, jobs, is_on_time_schedulable, select_job)
        t1 = time.time()
        opt_bb, _ = get_best_solution()

        # --- AMPL ---
        export_to_ampl_dat(jobs, filename=os.path.join(self.workdir, "instance.dat"))
        t2 = time.time()
        opt_ampl = run_ampl(
            model_file=self.model_file,
            data_file=os.path.join(self.workdir, "instance.dat"),
            solver=self.solver,
        )
        t3 = time.time()

        # --- AMPL rilassato (root) ---
        t4 = time.time()
        opt_relax = run_ampl_relax_node(
            relax_model_file=self.relax_model_file,
            T=set(),
            S=set(),
            jobs=jobs,
            data_file=os.path.join(self.workdir, "instance.dat"),
            solver=self.solver,
        )
        t5 = time.time()

        return {
            "opt_bb": opt_bb,
            "opt_ampl": opt_ampl,
            "opt_relax": opt_relax,
            "time_bb": t1 - t0,
            "time_ampl": t3 - t2,
            "time_relax": t5 - t4,
        }

    # ---------------------------
    # Test randomizzato
    # ---------------------------
    def run_random_tests(
        self,
        n_grid=(20, 40, 80),
        reps=3,
        r_range=(0, 0),
        p_range=(1, 5),
        tightness=0.2,
        seed_base=1000,
    ):
        gen = JobGenerator()

        print("\n== AMPL CORRECTNESS TEST ==")
        print(f"tightness={tightness}, r_range={r_range}, p_range={p_range}\n")

        total = 0

        for n in n_grid:
            for rep in range(reps):
                seed = seed_base + 100 * n + rep
                gen.seed = seed

                jobs = gen.generate(
                    n_jobs=n,
                    r_range=r_range,
                    p_range=p_range,
                    tightness=tightness,
                )

                res = self.solve_instance(jobs)
                total += 1

                ok = (res["opt_bb"] == res["opt_ampl"])
                status = "OK" if ok else "❌ FAIL"

                print(
                    f"n={n:3d} rep={rep} | "
                    f"BB={res['opt_bb']:3d}  "
                    f"AMPL={res['opt_ampl']:3d}  "
                    f"RELAX={res['opt_relax']:5.2f} | {status}"
                )

                if not ok:
                    print("\n❌ ERRORE DI CORRETTEZZA!")
                    print("Il modello AMPL NON coincide con il Branch & Bound.")
                    print("Interrompo il test.\n")
                    return False

        print("\n==============================")
        print(f"TEST COMPLETATI: {total}")
        print("✅ MODELLO AMPL CORRETTO")
        print("==============================\n")
        return True


if __name__ == "__main__":
    tester = AMPLCorrectnessTest(
        model_file="/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl_model/model.mod",
        relax_model_file="/home/giulia/Documenti/AMOD_project/Tardy-solver/ampl_model/relax_model.mod",
        solver="gurobi",
    )

    tester.run_random_tests(
        n_grid=(20, 40, 60, 80),
        reps=3,
        r_range=(0, 0),  # r_j = 0 → coerenza con Moore
        p_range=(1, 5),
        tightness=0.2,
    )
