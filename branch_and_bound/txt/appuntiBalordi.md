### Classe Node

## 1. A cosa servono quei `T: Set[int] = None` nel costruttore?

Questa è una **combinazione di type hinting + valore di default**, utile per inizializzare correttamente attributi *mutabili* come i set (o liste, dizionari...).

Vediamolo parte per parte:

```python
def __init__(self, T: Set[int] = None, ...)
```

- `T: Set[int]` è un **type hint** che indica che `T` dovrebbe essere un `set` di interi.
- `= None` è il **valore di default**, usato se chiami il costruttore senza passare `T`.

---

### Ma perché **non** usare direttamente `T: Set[int] = set()`?

⚠️ **Pericolo!**  
In Python, i valori di default sono valutati **una sola volta**, al momento della definizione della funzione.  
Quindi usare direttamente `set()` causerebbe la **condivisione dello stesso oggetto set tra tutte le istanze della classe**.  
È un classico errore:

```python
def __init__(self, T: Set[int] = set()):  # ⚠️ sbagliato!
```

---

### ✅ Soluzione sicura

Usando `None` come valore predefinito e poi inizializzando **dentro il corpo del costruttore**:

```python
self.T = set(T) if T is not None else set()
```

✅ In questo modo **crei un nuovo set ogni volta**, evitando condivisioni indesiderate tra istanze.

---



Perfetto, ora devo implementare un modulo che calcola il Branch and Bound (B&B), 