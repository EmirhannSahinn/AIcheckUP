# messagesPrep.py
import os
import csv

from message_action_16092025_0900 import message_action as message_action
from selection_action_16092025_0900 import (
    send_selection_quickreply as send_selection_quickreply,
    send_selection_card as send_selection_card,
    send_selection_list as send_selection_list,
)
from error_messages_16092025_0900 import error_messages as error_messages
from email_action_16092025_0900 import email_action as email_action


def runStep(label, func, *args, **kwargs):
    """Bir adımı çalıştır, sonucu logla."""
    try:
        func(*args, **kwargs)
        print(f"[OK] {label}")
        return True
    except FileNotFoundError as e:
        print(f"[ERROR] {label}: Dosya bulunamadı -> {e.filename}")
        return False
    except Exception as e:
        print(f"[ERROR] {label}: Beklenmeyen hata -> {e}")
        return False


def readKeySet(csv_path):
    """
    İçerik tabanlı anahtar seti döndürür:
    (row_id, node_id, node_name, node_type, module_type, source, text)
    """
    keys = set()
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return keys

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            keys.add((
                str(row.get("row_id", "")),
                str(row.get("node_id", "")),
                row.get("node_name", "") or "",
                row.get("node_type", "") or "",
                row.get("module_type", "") or "",
                row.get("source", "") or "",
                row.get("text", "") or "",
            ))
    return keys


def buildMessages(json_path, csv_path):
    """
    JSON'dan tek CSV'yi üretir/günceller ve csv_path döner.
    Yeni satırlar zaten aynı CSV'ye eklenir.
    İşlem sonrasında, önce-sonra farkına göre kaç yeni satır eklendiğini loglar.
    """
    if not os.path.exists(json_path):
        print(f"[FATAL] JSON dosyası bulunamadı: {json_path}")
        raise FileNotFoundError(json_path)

    # CSV klasörü yoksa oluştur
    csv_dir = os.path.dirname(csv_path)
    if csv_dir and not os.path.exists(csv_dir):
        os.makedirs(csv_dir, exist_ok=True)

    # 1) Çalıştırmadan ÖNCE mevcut satırların anahtar setini al
    pre_keys = readKeySet(csv_path)

    # 2) Adımlar (fonksiyonlar csv_utils ile yalnızca yeni satırları ekler)
    runStep("MESSAGE", message_action, json_path, csv_path)
    runStep("SELECTION / QUICKREPLY", send_selection_quickreply, json_path, csv_path)
    runStep("SELECTION / CARD", send_selection_card, json_path, csv_path)
    runStep("SELECTION / LIST", send_selection_list, json_path, csv_path)
    runStep("EMAIL", email_action, json_path, csv_path)
    runStep("OTHER ERROR MESSAGES", error_messages, json_path, csv_path)

    print(f"Tamamlandı. Çıktı: {csv_path}")

    # 3) SONRA: kaç yeni satır eklenmiş?
    post_keys = readKeySet(csv_path)
    new_count = len(post_keys - pre_keys)
    if new_count > 0:
        print(f"[delta] {new_count} yeni satır eklendi (aynı CSV).")
    else:
        print("[delta] Yeni satır yok (CSV değişmedi).")

    return csv_path
