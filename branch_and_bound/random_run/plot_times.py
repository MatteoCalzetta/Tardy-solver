import csv
import matplotlib.pyplot as plt
from collections import defaultdict


def plot_execution_times(csv_file):
    """
    Legge un file CSV di esperimenti e disegna un grafico
    Tempo di esecuzione vs Numero di job.
    """

    # Dizionari: n_jobs -> lista di tempi
    bb_times = defaultdict(list)
    ampl_times = defaultdict(list)
    relax_times = defaultdict(list)

    # Lettura CSV
    with open(csv_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            n = int(row["n_jobs"])
            bb_times[n].append(float(row["BB_time"]))
            ampl_times[n].append(float(row["AMPL_time"]))
            relax_times[n].append(float(row["RELAX_time"]))

    # Ordina i valori sull'asse X
    n_jobs_sorted = sorted(bb_times.keys())

    # Media dei tempi (utile se hai più istanze per stesso n)
    bb_avg = [sum(bb_times[n]) / len(bb_times[n]) for n in n_jobs_sorted]
    ampl_avg = [sum(ampl_times[n]) / len(ampl_times[n]) for n in n_jobs_sorted]
    relax_avg = [sum(relax_times[n]) / len(relax_times[n]) for n in n_jobs_sorted]

    # ---- Plot ----
    plt.figure(figsize=(8, 5))
    plt.plot(n_jobs_sorted, bb_avg, marker="o", label="Branch & Bound")
    plt.plot(n_jobs_sorted, ampl_avg, marker="s", label="AMPL (intero)")
    plt.plot(n_jobs_sorted, relax_avg, marker="^", label="AMPL (rilassato)")

    plt.xlabel("Numero di job")
    plt.ylabel("Tempo di esecuzione (secondi)")
    plt.title("Tempo di esecuzione vs Numero di job")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()


# ---- Esecuzione diretta ----
if __name__ == "__main__":
    plot_execution_times("results/results_experiments.csv")
