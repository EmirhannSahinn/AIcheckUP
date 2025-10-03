# error_messages.py
import json
import csv

from csv_utils_16092025_0900 import ensureHeader, loadKeySet, rowKey, nextRowId

FIELDNAMES = ["row_id", "node_id", "node_name", "node_type", "module_type", "source", "text"]

def error_messages(json_path, csv_path):
    """
    SELECTION ve MESSAGE dışındaki nodelarda errorMessage alanını CSV'ye ekler.
    Sütunlar: row_id,node_id,node_name,node_type,module_type,source,text
      - module_type: inputType | messageType | selectionType | moduleType | node_type (fallback)
      - source     : "ERRORMESSAGE"
      - text       : errorMessage
    Yalnızca daha önce eklenmemiş satırlar yazılır (tekilleştirme).
    """
    # JSON oku
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    nodes = data["nodes"]

    # CSV hazırlığı
    ensureHeader(csv_path, FIELDNAMES)
    existing_keys = loadKeySet(csv_path)
    row_id = nextRowId(csv_path)

    added = 0
    with open(csv_path, "a", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDNAMES)

        for node in nodes.values():
            node_type = node.get("type", "")
            if node_type in ("SELECTION", "MESSAGE"):
                continue  # sadece diğer node tipleri

            err = node.get("errorMessage")
            if not (isinstance(err, str) and err.strip()):
                continue

            node_id = node.get("id")
            node_name = node.get("name", "")

            # module_type: bulunabilen ilk alan; yoksa node_type
            module_type = (
                node.get("inputType")
                or node.get("messageType")
                or node.get("selectionType")
                or node.get("moduleType")
                or node_type
            )

            candidate = {
                "node_id": node_id,
                "node_name": node_name,
                "node_type": node_type,
                "module_type": module_type,
                "source": "ERRORMESSAGE",
                "text": err.strip(),
            }

            k = rowKey(candidate)
            if k in existing_keys:
                continue

            writer.writerow({"row_id": row_id, **candidate})
            existing_keys.add(k)
            row_id += 1
            added += 1

    print(f"[error_messages] {added} yeni satır eklendi.")
