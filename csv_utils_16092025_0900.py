# csv_utils.py
import os
import csv

# ---------------- Utilities ----------------

def norm(s):
    """Boşlukları sadeleştirip baş/son kırpar (case korunur)."""
    return " ".join(str(s or "").split())

def moduleValue(row):
    """Hem base CSV (module_type) hem review CSV (moduleType) için ortak okuma."""
    return row.get("module_type", row.get("moduleType", ""))

# ----------- Public API (camelCase) -----------

def rowKey(row):
    """
    Tekilleştirme anahtarı:
    (node_id, node_name, node_type, module_type|moduleType, source, text)
    """
    return (
        norm(row.get("node_id", "")),
        norm(row.get("node_name", "")),
        norm(row.get("node_type", "")),
        norm(moduleValue(row)),
        norm(row.get("source", "")),
        norm(row.get("text", "")),
    )

def loadKeySet(csv_path):
    """
    Var olan CSV'den tekilleştirme anahtarlarını set olarak döndürür.
    CSV yok/boşsa boş set döner.
    """
    keys = set()
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return keys
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            keys.add(rowKey(row))
    return keys

def nextRowId(csv_path):
    """
    Var olan CSV'de en büyük row_id + 1'i döndürür. CSV yok/boşsa 1 döner.
    """
    max_id = 0
    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    rid = int(str(row.get("row_id", "")).strip() or 0)
                    if rid > max_id:
                        max_id = rid
                except ValueError:
                    pass
    except FileNotFoundError:
        pass
    return max_id + 1

def ensureHeader(csv_path, fieldnames):
    """
    Dosya yoksa/boşsa header yazar. Varsa dokunmaz.
    """
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        with open(csv_path, "w", encoding="utf-8", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=fieldnames)
            writer.writeheader()

# ---------- Backward compatibility (aliases) ----------

row_key     = rowKey
load_keyset = loadKeySet
next_row_id = nextRowId
ensure_header = ensureHeader
