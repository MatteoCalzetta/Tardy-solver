from amplpy import AMPL

ampl = AMPL()
ampl.read("model.mod")

# passare i dati generati

ampl.get_parameter("n").set(n)
ampl.set["JOBS"] = range(1, n + 1)
ampl.get_parameter("r").setValues({i+1: r[i] for i in range(n)})
ampl.get_parameter("p").setValues({i+1: p[i] for i in range(n)})
ampl.get_parameter("d").setValues({i+1: d[i] for i in range(n)})

# Imposta solver
ampl.set_option("solver", "highs")

# Risolvi
ampl.solve()

# Mostra risultati
print("Valore ottimo:", ampl.get_objective("TotalTardy").value())

U = ampl.get_variable("U")
for j in range(1, n + 1):
    print(f"Job {j} tardy:", int(U[j].value()))