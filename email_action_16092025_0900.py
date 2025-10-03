# email_action.py
import json
import re
import html
import csv

from csv_utils_16092025_0900 import ensureHeader, loadKeySet, rowKey, nextRowId

FIELDNAMES = ["row_id", "node_id", "node_name", "node_type", "module_type", "source", "text"]

def clean_html(s):
    """
    HTML etiketlerini kaldırır, HTML entity'lerini çözer ve boşlukları sadeleştirir.
    """
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)   # tüm HTML etiketlerini çıkar
    s = re.sub(r"\s+", " ", s)       # çoklu boşlukları tek boşluğa indir
    return s.strip()

def email_action(json_path, csv_path):
    """
    EMAIL nodelarından metinleri CSV'ye ekler (append).
    Kaynaklar:
      - emailSubject  -> source: EMAIL/SUBJECT
      - emailTemplate -> source: EMAIL/BODY (HTML temizlenir)
    Not: Sadece daha önce eklenmemiş satırlar yazılır (tekilleştirme).
    """
    # JSON'u oku
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    nodes = data["nodes"]

    # CSV header'ı garanti et, mevcut anahtar setini ve başlangıç row_id'yi al
    ensureHeader(csv_path, FIELDNAMES)
    existing_keys = loadKeySet(csv_path)
    row_id = nextRowId(csv_path)

    added = 0
    with open(csv_path, "a", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDNAMES)

        for node in nodes.values():
            if node.get("type") != "EMAIL":
                continue

            node_id = node.get("id")
            node_name = node.get("name", "")
            node_type = node.get("type", "")
            module_type = node.get("emailType") or node_type  # yoksa node_type kullan

            # emailSubject -> EMAIL/SUBJECT
            subj = node.get("emailSubject")
            if isinstance(subj, str) and subj.strip():
                candidate = {
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                    "module_type": module_type,
                    "source": "EMAIL/SUBJECT",
                    "text": subj.strip(),
                }
                if rowKey(candidate) not in existing_keys:
                    writer.writerow({"row_id": row_id, **candidate})
                    existing_keys.add(rowKey(candidate))
                    row_id += 1
                    added += 1

            # emailTemplate (HTML) -> EMAIL/BODY
            body = node.get("emailTemplate")
            if isinstance(body, str) and body.strip():
                clean_body = clean_html(body)
                if clean_body:
                    candidate = {
                        "node_id": node_id,
                        "node_name": node_name,
                        "node_type": node_type,
                        "module_type": module_type,
                        "source": "EMAIL/BODY",
                        "text": clean_body,
                    }
                    if rowKey(candidate) not in existing_keys:
                        writer.writerow({"row_id": row_id, **candidate})
                        existing_keys.add(rowKey(candidate))
                        row_id += 1
                        added += 1

    print(f"[email_action] {added} yeni satır eklendi.")
