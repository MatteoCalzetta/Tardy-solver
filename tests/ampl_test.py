from amplpy import AMPL
from pathlib import Path

# Percorso base del progetto
BASE = Path("/home/giulia/Documenti/AMOD_project/Tardy_solver/ampl_model")
MODEL = BASE / "model.mod"
TESTS = BASE / "test_dat"

tests = [
    ("test_all_on_time.dat", 0),
    ("test_one_tardy.dat", 1),
    ("test_k_tardy_block.dat", 3),
    ("test_release_forced.dat", 1),
    ("test_symmetry_many_opt.dat", 2),
]

def run_ampl_test(datfile, expected_opt):
    ampl = AMPL()
    ampl.set_option("solver", "gurobi")

    ampl.read(str(MODEL))
    ampl.read_data(str(TESTS / datfile))
    ampl.solve()

    opt = ampl.get_objective("TotalTardy").value()
    print(f"\n[{datfile}] obiettivo = {opt}, atteso = {expected_opt} -> "
          f"{'✅ PASS' if opt == expected_opt else '❌ FAIL'}")

if __name__ == "__main__":
    print("=== Esecuzione test AMPL ===")
    for dat, exp in tests:
        run_ampl_test(dat, exp)
