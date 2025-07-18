class BnBStats:
    def __init__(self):
        self.nodi_generati = 0
        self.profondità_totale = 0
        self.chiamate_lb = 0
        self.tempo_totale_lb = 0.0
        self.fathom_lb = 0
        self.fathom_leaf = 0

    def reset(self):
        self.__init__()

    def print_summary(self, best_int, best_sol):
        print("=== STATISTICHE B&B ===")
        print(f"Soluzione migliore: tardy = {best_int}, T = {sorted(best_sol)}")
        print(f"Nodi generati: {self.nodi_generati}")
        if self.nodi_generati > 0:
            print(f"Profondità media: {self.profondità_totale / self.nodi_generati:.2f}")
        print(f"Chiamate compute_lb: {self.chiamate_lb}")
        print(f"Tempo totale compute_lb: {self.tempo_totale_lb:.4f} sec")
        print(f"Fathoming per bound: {self.fathom_lb}")
        print(f"Fathoming per foglia: {self.fathom_leaf}")
