# message_action.py
import json
import csv

from csv_utils_16092025_0900 import ensureHeader, loadKeySet, rowKey, nextRowId

FIELDNAMES = ["row_id", "node_id", "node_name", "node_type", "module_type", "source", "text"]

def message_action(json_path, csv_path):
    """
    MESSAGE nodeları → payloads’taki her metin için satır üretir.
    CSV’ye yazarken tekrarlayanları (node_id,node_name,node_type,module_type,source,text) otomatik atlar.
    payloads yok/boşsa tek satır boş text ile yazar.
    """
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

        for key, node in nodes.items():
            if node.get("type") != "MESSAGE":
                continue

            node_id = node.get("id", key)
            node_name = node.get("name", "")
            node_type = node.get("type", "")
            module_type = node.get("messageType", "")
            source = module_type  # istenen davranış: source = module_type

            payloads = node.get("payloads")
            if isinstance(payloads, list) and payloads:
                texts = [str(p).strip() for p in payloads]
            elif isinstance(payloads, (str, int, float)):
                texts = [str(payloads).strip()]
            else:
                texts = [""]  # payloads yok/boş ise tek satır boş text

            for txt in texts:
                candidate = {
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                    "module_type": module_type,
                    "source": source,
                    "text": txt,
                }
                k = rowKey(candidate)
                if k in existing_keys:
                    continue

                writer.writerow({"row_id": row_id, **candidate})
                existing_keys.add(k)
                row_id += 1
                added += 1

    print(f"[message_action] {added} yeni satır eklendi.")
