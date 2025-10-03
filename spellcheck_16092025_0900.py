# spellcheck.py
# ngrok http 8000
# -*- coding: utf-8 -*-

"""
# (UZAK VM terminalinde)
# 0) Gerekli dosya ve venv var mı?
ls -l /opt/myapp/codes/spellcheck_15092025_1300.py
ls -l /opt/myapp/.venv/bin/python || python3 -m venv /opt/myapp/.venv

# 1) Servis dosyasını oluştur (tüm bloğu tek seferde yapıştır)
sudo tee /etc/systemd/system/myapp.service >/dev/null <<'EOF'
[Unit]
Description=My Python App
After=network-online.target
Wants=network-online.target

[Service]
User=azureuser
WorkingDirectory=/opt/myapp
Environment="PYTHONUNBUFFERED=1"
# EnvironmentFile=/opt/myapp/.env   # .env kullanıyorsanız bu satırı açın

ExecStart=/opt/myapp/.venv/bin/python /opt/myapp/codes/spellcheck_16092025_0900.py

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 2) Systemd'yi yenile ve servisi başlat
sudo systemctl daemon-reload
sudo systemctl enable --now myapp

# 3) Durumu ve logları kontrol et
systemctl status myapp --no-pager
journalctl -u myapp -f   # izin gerekirse: sudo journalctl -u myapp -f
"""


"""
sudo systemctl stop myapp
# bir daha açılışta başlamasın dersen:
sudo systemctl disable myapp
# durum kontrol
systemctl is-active myapp
"""
import os
import csv
import json
import re
import time

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from prompts_16092025_0900 import render_prompt
from messagesPrep_16092025_0900 import buildMessages

# ----------------------------
# PATH'LER
# ----------------------------
""" JSON_PATH         = "/Users/emirhansahin/Desktop/Desktop/Mapathon/project2/data/akmerkez/app/Akmerkez TR App_design.json"
MESSAGES_CSV_PATH = "/Users/emirhansahin/Desktop/Desktop/Mapathon/project2/output/akmerkez/app/akmerkez_app_messages2.csv"
OUTPUT_CSV_PATH   = "/Users/emirhansahin/Desktop/Desktop/Mapathon/project2/output/akmerkez/app/akmerkez_app_output2.csv" """

# -*- coding: utf-8 -*-
# dosyanın başlarına ekle
TASK_ENDS = {}  # hangi taskların finally'e girdiğini işaretlemek için


import sys

from contextlib import contextmanager

# Her task için "Bitti." satırını bir kez yazalım
_DONE_PRINTED = set()
def _mark_done(tag: str):
    if tag not in _DONE_PRINTED:
        print(f"[{tag}] Bitti.", flush=True)
        _DONE_PRINTED.add(tag)

@contextmanager
def section(tag: str):
    try:
        yield
    finally:
        _mark_done(tag)   # sarmalayıcı çıkarken garanti "Bitti."


try:
    sys.stdout.reconfigure(line_buffering=True)  # canlı satır akışı
except Exception:
    pass

import argparse, os

parser = argparse.ArgumentParser()
parser.add_argument("--json", required=True, help="Girdi JSON dosyası")
parser.add_argument("--output_csv", required=True, help="Çıktı CSV dosyası")
parser.add_argument("--messages_csv", required=False, help="Ara çıktı messages.csv (opsiyonel)")
parser.add_argument("--target_tone", required=False, default="", help="Hedef ton (ör. tr-formal, en-casual)")
args = parser.parse_args()

JSON_PATH       = args.json
OUTPUT_CSV_PATH = args.output_csv

if args.messages_csv:
    MESSAGES_CSV_PATH = args.messages_csv
else:
    out_dir = os.path.dirname(os.path.abspath(OUTPUT_CSV_PATH)) or "."
    MESSAGES_CSV_PATH = os.path.join(out_dir, "messages.csv")

TARGET_TONE = args.target_tone or "tr-formal"

print(f"TARGET_TONE={TARGET_TONE}", flush=True)
print(f"JSON={JSON_PATH}", flush=True)
print(f"OUTPUT_CSV={OUTPUT_CSV_PATH}", flush=True)
print(f"MESSAGES_CSV={MESSAGES_CSV_PATH}", flush=True)



# ----------------------------
# KONTROLLER
# ----------------------------
TARGET_TONE   = "Siz dili"
DELAY_SECONDS = 0.1

# ----------------------------
# OpenAI
# ----------------------------
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY bulunamadı. Ortam değişkeni ya da .env ile sağlayın.")
OPENAI_MODEL = "gpt-4.1"
client = OpenAI(api_key=API_KEY)

# ----------------------------
# Yardımcılar
# ----------------------------
def norm(s: str) -> str:
    return " ".join((s or "").split())

# ----------------------------
# CSV Yardımcıları
# ----------------------------
OUT_FIELDS = [
    "row_id",
    "node_id", "node_name", "node_type", "module_type", "source", "text",
    "spellCheck", "spellCorrect",
    "grammarCheck", "grammarCorrect",
    "puncCheck", "puncCorrect",
    "clarityCheck", "clarityCorrect",
    "toneCheck", "toneCorrect",
]

def ensureMessagesCsv():
    print("[prep] JSON->messages.csv hazırlanıyor...")
    buildMessages(JSON_PATH, MESSAGES_CSV_PATH)

def ensureOutputCsv():
    out_dir = os.path.dirname(OUTPUT_CSV_PATH)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    if os.path.exists(OUTPUT_CSV_PATH) and os.path.getsize(OUTPUT_CSV_PATH) > 0:
        print(f"[prep] Çıktı CSV mevcut: {OUTPUT_CSV_PATH}")
        return

    print(f"[prep] Çıktı CSV oluşturuluyor: {OUTPUT_CSV_PATH}")
    with open(MESSAGES_CSV_PATH, "r", encoding="utf-8", newline="") as src, \
         open(OUTPUT_CSV_PATH, "w", encoding="utf-8", newline="") as dst:
        r = csv.DictReader(src)
        w = csv.DictWriter(dst, fieldnames=OUT_FIELDS)
        w.writeheader()
        for row in r:
            w.writerow({
                "row_id": row.get("row_id", ""),
                "node_id": row.get("node_id", ""),
                "node_name": row.get("node_name", ""),
                "node_type": row.get("node_type", ""),
                "module_type": row.get("module_type", ""),
                "source": row.get("source", ""),
                "text": (row.get("text") or "").strip(),
                "spellCheck": "", "spellCorrect": "",
                "grammarCheck": "", "grammarCorrect": "",
                "puncCheck": "", "puncCorrect": "",
                "clarityCheck": "", "clarityCorrect": "",
                "toneCheck": "", "toneCorrect": "",
            })

def readOutputRows():
    rows = []
    with open(OUTPUT_CSV_PATH, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            # Eski dosyalarda moduleType olabilir -> module_type'a normalize et
            if "module_type" not in row or (not row.get("module_type") and row.get("moduleType")):
                row["module_type"] = row.get("moduleType", row.get("module_type", ""))
            rows.append(row)
    return rows

def writeOutputRows(rows):
    with open(OUTPUT_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        for r in rows:
            # Yazmadan önce module_type alanını garanti et
            if "module_type" not in r or (not r.get("module_type") and r.get("moduleType")):
                r["module_type"] = r.get("moduleType", r.get("module_type", ""))
            for k in OUT_FIELDS:
                r.setdefault(k, "")
            w.writerow(r)

def rowIdentityKey(r):
    return (
        str(r.get("row_id", "")),
        str(r.get("node_id", "")),
        r.get("node_name", ""),
        r.get("node_type", ""),
        r.get("module_type", ""),
        r.get("source", ""),
        r.get("text", ""),
    )

def setResult(rows, key, check_col, correct_col, check_val, correct_val):
    for r in rows:
        if rowIdentityKey(r) == key:
            r[check_col] = check_val
            r[correct_col] = correct_val
            return True
    return False

def baseToOutRow(base):
    return {
        "row_id": base.get("row_id", ""),
        "node_id": base.get("node_id", ""),
        "node_name": base.get("node_name", ""),
        "node_type": base.get("node_type", ""),
        "module_type": base.get("module_type", ""),
        "source": base.get("source", ""),
        "text": (base.get("text") or "").strip(),
        "spellCheck": "", "spellCorrect": "",
        "grammarCheck": "", "grammarCorrect": "",
        "puncCheck": "", "puncCorrect": "",
        "clarityCheck": "", "clarityCorrect": "",
        "toneCheck": "", "toneCorrect": "",
    }

def baseIdentityKey(base):
    return (
        str(base.get("row_id", "")),
        str(base.get("node_id", "")),
        base.get("node_name", ""),
        base.get("node_type", ""),
        base.get("module_type", ""),
        base.get("source", ""),
        (base.get("text") or "").strip(),
    )

def syncOutputWithMessages(messages_csv_path, output_csv_path):
    if not (os.path.exists(output_csv_path) and os.path.getsize(output_csv_path) > 0):
        ensureOutputCsv()

    out_rows = readOutputRows()

    out_keys_with = set(rowIdentityKey(r) for r in out_rows)
    def key_wo_rowid(r):
        return (
            str(r.get("node_id", "")),
            r.get("node_name", ""),
            r.get("node_type", ""),
            r.get("module_type", ""),
            r.get("source", ""),
            r.get("text", ""),
        )
    out_keys_wo = set(key_wo_rowid(r) for r in out_rows)
    idx_map_wo = { key_wo_rowid(r): i for i, r in enumerate(out_rows) }

    added = 0
    with open(messages_csv_path, "r", encoding="utf-8", newline="") as f:
        base_reader = csv.DictReader(f)
        for base in base_reader:
            key = baseIdentityKey(base)
            out_style_key_with = (
                key[0],  # row_id
                key[1],  # node_id
                key[2],  # node_name
                key[3],  # node_type
                key[4],  # module_type
                key[5],  # source
                key[6],  # text
            )
            out_style_key_wo = (
                key[1],  # node_id
                key[2],  # node_name
                key[3],  # node_type
                key[4],  # module_type
                key[5],  # source
                key[6],  # text
            )

            if out_style_key_with in out_keys_with:
                continue

            if out_style_key_wo in out_keys_wo:
                i = idx_map_wo[out_style_key_wo]
                if not out_rows[i].get("row_id"):
                    out_rows[i]["row_id"] = key[0]
                    out_keys_with.add(rowIdentityKey(out_rows[i]))
                continue

            out_rows.append(baseToOutRow(base))
            out_keys_with.add(out_style_key_with)
            out_keys_wo.add(out_style_key_wo)
            idx_map_wo[out_style_key_wo] = len(out_rows) - 1
            added += 1

    if added or out_rows:
        writeOutputRows(out_rows)
    if added:
        print(f"[sync] {output_csv_path} dosyasına {added} yeni satır eklendi.")
    else:
        print("[sync] Eklenecek yeni satır yok (output güncel).")
    return added

# ----------------------------
# OpenAI Çağrısı ve JSON Parse
# ----------------------------
JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)

def extractFirstJSON(text):
    if not isinstance(text, str):
        return None
    m = JSON_OBJECT_RE.search(text)
    return m.group(0) if m else None

def callOpenAI(task, text, tone=None):
    if task == "tone":
        system_msg, user_msg = render_prompt(task, text=text, tone=(tone or ""))
    else:
        system_msg, user_msg = render_prompt(task, text=text)

    resp = client.responses.create(
        model=OPENAI_MODEL,
        instructions=system_msg.strip(),
        input=user_msg.strip(),
        temperature=0,
    )
    raw = getattr(resp, "output_text", None) or str(resp)
    js = extractFirstJSON(raw)
    if not js:
        return {"0": []}
    try:
        parsed = json.loads(js)
        if "1" in parsed and isinstance(parsed["1"], list):
            return {"1": parsed["1"]}
        if "0" in parsed and isinstance(parsed["0"], list):
            return {"0": []}
        return {"0": []}
    except Exception:
        return {"0": []}

def parseListCell(cell):
    if not isinstance(cell, str) or not cell.strip():
        return []
    try:
        val = json.loads(cell)
        return val if isinstance(val, list) else []
    except Exception:
        return []

# ----------------------------
# Ek Kurallar (punct/clarity/tone)
# ----------------------------
def applySecondaryRule(task, current_row, result_list):
    if task not in ("punctuation", "clarity", "tone"):
        return ("1" if result_list else "0", result_list)

    grammar_check = (current_row.get("grammarCheck") or "").strip()
    grammar_correct_list = parseListCell(current_row.get("grammarCorrect") or "")
    text_val = (current_row.get("text") or "").strip()

    res_norm  = [norm(x) for x in result_list]
    gram_norm = [norm(x) for x in grammar_correct_list]
    text_norm = norm(text_val)

    if grammar_check == "1" and set(res_norm) == set(gram_norm):
        return ("0", [])

    if grammar_check == "0" and any(x == text_norm for x in res_norm):
        return ("0", [])

    return ("1" if result_list else "0", result_list)

# ----------------------------
# Görev Çalıştırıcı
# ----------------------------
""" def processTask(task, check_col, correct_col, tone=None):
    print(f"[{task}] başlıyor...")
    rows = readOutputRows()

    todo_keys = []
    for r in rows:
        if not (r.get("text") or "").strip():
            continue
        if (r.get(check_col) or "").strip() != "":
            continue
        todo_keys.append(rowIdentityKey(r))

    total = len(todo_keys)
    if total == 0:
        print(f"[{task}] İşlenecek satır yok.")
        return
    print(f"[{task}] İşlenecek satır sayısı: {total}")

    for idx, key in enumerate(todo_keys, 1):
        current_row = next((rr for rr in rows if rowIdentityKey(rr) == key), None)
        if current_row is None:
            continue

        text = (current_row.get("text") or "").strip()
        try:
            result = callOpenAI(task, text, tone=tone)
            corrected_list = result.get("1", []) if "1" in result else []

            check_val, corrected_list = applySecondaryRule(task, current_row, corrected_list)

            correct_cell = "" if check_val == "0" else json.dumps(corrected_list, ensure_ascii=False)

            setResult(rows, key, check_col, correct_col, check_val, correct_cell)

            writeOutputRows(rows)
            rid = current_row.get("row_id", "")
            nid = current_row.get("node_id", "")
            print(f"[{task}] {idx}/{total} OK: row_id={rid}, node_id={nid}, check={check_val}")
        except Exception as e:
            print(f"[{task}] Hata (satır {idx}/{total}): {e}")

        if DELAY_SECONDS and DELAY_SECONDS > 0:
            time.sleep(DELAY_SECONDS)

    print(f"[{task}] Bitti.") """



def processTask(task, check_col, correct_col, tone=None):
    print(f"[{task}] Başladı.", flush=True)
    try:
        rows = readOutputRows()

        todo_keys = []
        for r in rows:
            if not (r.get("text") or "").strip():
                continue
            if (r.get(check_col) or "").strip() != "":
                continue
            todo_keys.append(rowIdentityKey(r))

        total = len(todo_keys)
        if total == 0:
            print(f"[{task}] İşlenecek satır yok.", flush=True)
            return  # section() yine çıkışta "Bitti." yazacak

        print(f"[{task}] İşlenecek satır sayısı: {total}", flush=True)

        for idx, key in enumerate(todo_keys, 1):
            current_row = next((rr for rr in rows if rowIdentityKey(rr) == key), None)
            if current_row is None:
                continue

            text = (current_row.get("text") or "").strip()
            try:
                result = callOpenAI(task, text, tone=tone)
                corrected_list = result.get("1", []) if "1" in result else []

                check_val, corrected_list = applySecondaryRule(task, current_row, corrected_list)
                correct_cell = "" if check_val == "0" else json.dumps(corrected_list, ensure_ascii=False)

                setResult(rows, key, check_col, correct_col, check_val, correct_cell)
                writeOutputRows(rows)

                rid = current_row.get("row_id", "")
                nid = current_row.get("node_id", "")
                print(f"[{task}] {idx}/{total} OK: row_id={rid}, node_id={nid}, check={check_val}", flush=True)
            except Exception as e:
                print(f"[{task}] Hata (satır {idx}/{total}): {e}", flush=True)

            if DELAY_SECONDS and DELAY_SECONDS > 0:
                time.sleep(DELAY_SECONDS)

    finally:
        _mark_done(task)   # << sadece bunu çağır, print yok




# ----------------------------
# Ana Akış
# ----------------------------
""" if __name__ == "__main__":
    ensureMessagesCsv()
    ensureOutputCsv()
    syncOutputWithMessages(MESSAGES_CSV_PATH, OUTPUT_CSV_PATH)

    processTask("spellcheck",  "spellCheck",  "spellCorrect")
    processTask("grammar",     "grammarCheck","grammarCorrect")
    processTask("punctuation", "puncCheck",   "puncCorrect")
    processTask("clarity",     "clarityCheck","clarityCorrect")
    processTask("tone",        "toneCheck",   "toneCorrect", tone=TARGET_TONE)

    print(f"[done] Çıktı güncellendi: {OUTPUT_CSV_PATH}") """

# ----------------------------
# Ana Akış
# ----------------------------
if __name__ == "__main__":
    ensureMessagesCsv()
    ensureOutputCsv()
    syncOutputWithMessages(MESSAGES_CSV_PATH, OUTPUT_CSV_PATH)

    with section("spellcheck"):
        processTask("spellcheck",  "spellCheck",  "spellCorrect")

    with section("grammar"):
        processTask("grammar",     "grammarCheck","grammarCorrect")

    with section("punctuation"):
        processTask("punctuation", "puncCheck",   "puncCorrect")

    with section("clarity"):
        processTask("clarity",     "clarityCheck","clarityCorrect")

    with section("tone"):
        processTask("tone",        "toneCheck",   "toneCorrect", tone=TARGET_TONE)

    print(f"[done] Çıktı güncellendi: {OUTPUT_CSV_PATH}", flush=True)

