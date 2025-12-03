import os
import sys
import argparse
import pandas as pd
import matplotlib.pyplot as plt


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def read_csv_safe(path: str) -> pd.DataFrame | None:
    if not os.path.exists(path):
        print(f"[WARN] CSV non trovato: {path}")
        return None
    try:
        df = pd.read_csv(path)
        if df.empty:
            print(f"[WARN] CSV vuoto: {path}")
            return None
        return df
    except Exception as e:
        print(f"[WARN] Impossibile leggere {path}: {e}")
        return None


def agg_mean_std(df: pd.DataFrame, by: str, cols: list[str]) -> pd.DataFrame:
    """
    Raggruppa per `by` e calcola mean/std per le colonne in `cols`.
    Ritorna un DataFrame con colonne flattenate, es:
        n, runtime_s_mean, runtime_s_std
    """
    g = df.groupby(by)[cols].agg(['mean', 'std']).reset_index()
    # appiattisci MultiIndex colonne
    new_cols = []
    for c in g.columns.values:
        if isinstance(c, tuple):
            base, agg = c
            if agg == '':
                new_cols.append(base)
            else:
                new_cols.append(f"{base}_{agg}")
        else:
            new_cols.append(c)
    g.columns = new_cols

    # rinomina chiave raggruppamento se serve (es. "n_" -> "n")
    if f"{by}_" in g.columns:
        g = g.rename(columns={f"{by}_": by})

    return g


def _table_path_from_plot_path(plot_path: str, suffix: str = "_table.csv") -> str:
    """
    Dato il path del PNG, genera un path per la tabella CSV.
    Esempio:
        runtime_vs_n.png -> runtime_vs_n_table.csv
    """
    root, ext = os.path.splitext(plot_path)
    return root + suffix


def save_table(df: pd.DataFrame, plot_out_path: str, label: str):
    """
    Salva un DataFrame come CSV, usando il path del plot per derivare il nome.
    """
    table_path = _table_path_from_plot_path(plot_out_path)
    try:
        df.to_csv(table_path, index=False)
        print(f"[OK] Tabella {label} salvata: {table_path}")
    except Exception as e:
        print(f"[WARN] Impossibile salvare tabella {label} in {table_path}: {e}")


def plot_runtime_vs_n(df: pd.DataFrame, out_path: str):
    req = ['n', 'runtime_s']
    if not all(c in df.columns for c in req):
        print("[WARN] Colonne mancanti per runtime_vs_n:", req)
        return

    g = agg_mean_std(df, by='n', cols=['runtime_s'])

    # salva tabella aggregata
    save_table(g, out_path, label="runtime_vs_n")

    x = g['n']
    y = g['runtime_s_mean']
    e = g['runtime_s_std']

    plt.figure()
    plt.errorbar(x, y, yerr=e, fmt='-o', capsize=4)
    plt.yscale('log')
    plt.xlabel('n (numero job)')
    plt.ylabel('Runtime medio [s] (scala log)')
    plt.title('Tempo di esecuzione vs n')
    plt.grid(True, which='both', linestyle=':')
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
    print(f"[OK] Salvato: {out_path}")


def plot_gap_vs_n(df: pd.DataFrame, out_path: str):
    req = ['n', 'gap']
    if not all(c in df.columns for c in req):
        print("[WARN] Colonne mancanti per gap_vs_n:", req)
        return

    g = agg_mean_std(df, by='n', cols=['gap'])

    # salva tabella aggregata
    save_table(g, out_path, label="gap_vs_n")

    x = g['n']
    y = g['gap_mean']
    e = g['gap_std']

    plt.figure()
    plt.errorbar(x, y, yerr=e, fmt='-o', capsize=4)
    plt.xlabel('n (numero job)')
    plt.ylabel('Gap medio (UB - Opt)')
    plt.title('Gap euristica (EDD) vs n')
    plt.grid(True, linestyle=':')
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
    print(f"[OK] Salvato: {out_path}")


def plot_nodes_vs_n(df: pd.DataFrame, out_path: str):
    req = ['n', 'nodes']
    if not all(c in df.columns for c in req):
        print("[WARN] Colonne mancanti per nodes_vs_n:", req)
        return

    g = agg_mean_std(df, by='n', cols=['nodes'])

    # salva tabella aggregata
    save_table(g, out_path, label="nodes_vs_n")

    x = g['n']
    y = g['nodes_mean']
    e = g['nodes_std']

    plt.figure()
    plt.errorbar(x, y, yerr=e, fmt='-o', capsize=4)
    plt.xlabel('n (numero job)')
    plt.ylabel('Nodi medi esplorati')
    plt.title('Nodi esplorati vs n')
    plt.grid(True, which='both', linestyle=':')
    plt.ylim(bottom=0)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
    print(f"[OK] Salvato: {out_path}")


def plot_ablation_runtime(df: pd.DataFrame, out_path: str):
    req = ['config', 'runtime_s']
    if not all(c in df.columns for c in req):
        print("[WARN] Colonne mancanti per ablation_runtime:", req)
        return

    g = agg_mean_std(df, by='config', cols=['runtime_s'])

    # salva tabella aggregata
    save_table(g, out_path, label="ablation_runtime")

    x = g['config']
    y = g['runtime_s_mean']
    e = g['runtime_s_std']

    plt.figure()
    plt.bar(x, y, yerr=e, capsize=4)
    plt.xlabel('Configurazione LB')
    plt.ylabel('Runtime medio [s]')
    plt.title('Ablation LB: runtime per configurazione')
    plt.grid(True, axis='y', linestyle=':')
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
    print(f"[OK] Salvato: {out_path}")


def plot_ablation_nodes(df: pd.DataFrame, out_path: str):
    req = ['config', 'nodes']
    if not all(c in df.columns for c in req):
        print("[WARN] Colonne mancanti per ablation_nodes:", req)
        return

    g = agg_mean_std(df, by='config', cols=['nodes'])

    # salva tabella aggregata
    save_table(g, out_path, label="ablation_nodes")

    x = g['config']
    y = g['nodes_mean']
    e = g['nodes_std']

    plt.figure()
    plt.bar(x, y, yerr=e, capsize=4)
    plt.yscale('log')
    plt.xlabel('Configurazione LB')
    plt.ylabel('Nodi medi (scala log)')
    plt.title('Ablation LB: nodi esplorati per configurazione')
    plt.grid(True, axis='y', which='both', linestyle=':')
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
    print(f"[OK] Salvato: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Plot dei CSV generati da experiments.py")
    parser.add_argument("--results-dir", type=str,
                        default=os.path.join("results"),
                        help="Directory che contiene i CSV")
    parser.add_argument("--out-dir", type=str,
                        default=os.path.join("plots"),
                        help="Directory di output per i PNG (e tabelle CSV)")
    parser.add_argument("--prefix", type=str, default="",
                        help="Prefisso facoltativo per i nomi dei PNG")
    args = parser.parse_args()

    ensure_dir(args.out_dir)

    # --- scaling n ---
    scaling_csv = os.path.join(args.results_dir, "results_scaling_n.csv")
    df_scal = read_csv_safe(scaling_csv)
    if df_scal is not None:
        plot_runtime_vs_n(df_scal, os.path.join(args.out_dir, f"{args.prefix}runtime_vs_n.png"))
        plot_gap_vs_n(df_scal,     os.path.join(args.out_dir, f"{args.prefix}gap_vs_n.png"))
        plot_nodes_vs_n(df_scal,   os.path.join(args.out_dir, f"{args.prefix}nodes_vs_n.png"))

    # --- ablation LB ---
    ablation_csv = os.path.join(args.results_dir, "results_lb_ablation.csv")
    df_abl = read_csv_safe(ablation_csv)
    if df_abl is not None:
        plot_ablation_runtime(df_abl, os.path.join(args.out_dir, f"{args.prefix}ablation_runtime.png"))
        plot_ablation_nodes(df_abl,   os.path.join(args.out_dir, f"{args.prefix}ablation_nodes.png"))

    print(f"[DONE] Grafici e tabelle salvati in: {args.out_dir}")


if __name__ == "__main__":
    main()
