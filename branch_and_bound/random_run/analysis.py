import os
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------------
# Funzione per calcolare i gap %
# -------------------------------
def compute_gaps(csv_file, output_csv_file=None):
    """
    Legge un CSV con i risultati degli esperimenti, calcola i gap percentuali
    rispetto al Branch & Bound (BB) e salva i nuovi dati in un CSV aggiornato.
    
    Gap percentuali calcolati:
        - GAP_AMPL = (AMPL_tardy - BB_tardy) / BB_tardy * 100
        - GAP_RELAX = (RELAX_tardy - BB_tardy) / BB_tardy * 100
    
    Args:
        csv_file (str): percorso del CSV con i dati originali
        output_csv_file (str, opzionale): percorso del CSV aggiornato.
            Se None, sovrascrive il CSV originale.
    Returns:
        pd.DataFrame: DataFrame con le colonne dei gap aggiunte
    """
    df = pd.read_csv(csv_file)

    # Evita divisione per zero
    df['GAP_AMPL'] = ((df['AMPL_tardy'] - df['BB_tardy']) / df['BB_tardy'].replace(0, 1)) * 100
    df['GAP_RELAX'] = ((df['RELAX_tardy'] - df['BB_tardy']) / df['BB_tardy'].replace(0, 1)) * 100

    # Salva CSV aggiornato
    if output_csv_file is None:
        output_csv_file = csv_file

    df.to_csv(output_csv_file, index=False)
    print(f"CSV aggiornato salvato in '{output_csv_file}' con colonne GAP_AMPL e GAP_RELAX.")

    return df

# -------------------------------
# Funzione per stampare i grafici
# -------------------------------
def plot_results(csv_file):
    """
    Legge un CSV con risultati e gap, e stampa 2 grafici separati:
        1) Tempi di esecuzione in funzione del numero di job
        2) Gap percentuali in funzione del numero di job

    Args:
        csv_file (str): percorso del CSV aggiornato con colonne GAP_AMPL e GAP_RELAX
    """
    df = pd.read_csv(csv_file)

    # Grafico 1: Tempi
    plt.figure(figsize=(10, 5))
    plt.plot(df['n_jobs'], df['BB_time'], marker='o', label='BB')
    plt.plot(df['n_jobs'], df['AMPL_time'], marker='o', label='AMPL')
    plt.plot(df['n_jobs'], df['RELAX_time'], marker='o', label='RELAX')
    plt.xlabel("Numero di Job")
    plt.ylabel("Tempo (s)")
    plt.title("Andamento tempi di esecuzione")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # Grafico 2: Gap percentuali
    plt.figure(figsize=(10, 5))
    plt.plot(df['n_jobs'], df['GAP_AMPL'], marker='o', label='GAP AMPL %')
    plt.plot(df['n_jobs'], df['GAP_RELAX'], marker='o', label='GAP RELAX %')
    plt.xlabel("Numero di Job")
    plt.ylabel("Gap percentuale (%)")
    plt.title("Gap percentuali rispetto al Branch & Bound")
    plt.axhline(0, color='gray', linestyle='--')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# -------------------------------
# Esempio di uso
# -------------------------------
if __name__ == "__main__":
    csv_file = "results_experiments.csv"  # CSV originale generato dal main
    df = compute_gaps(csv_file)           # calcola gap e aggiorna CSV
    plot_results(csv_file)                # stampa grafici
