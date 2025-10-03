# selection_action.py
import json
import csv

from csv_utils_16092025_0900 import ensureHeader, loadKeySet, rowKey, nextRowId

FIELDNAMES = ["row_id", "node_id", "node_name", "node_type", "module_type", "source", "text"]


def send_selection_quickreply(json_path, csv_path):
    """
    SELECTION/QUICKREPLY:
      - payloads[*].text  -> BUTTON/<payload_type>
      - prompt            -> PROMPT
      - errorMessage      -> ERRORMESSAGE
    Yalnızca yeni satırlar CSV'ye eklenir (tekilleştirme).
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    nodes = data["nodes"]

    ensureHeader(csv_path, FIELDNAMES)
    existing_keys = loadKeySet(csv_path)
    row_id = nextRowId(csv_path)

    added = 0
    with open(csv_path, "a", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=FIELDNAMES)

        for node in nodes.values():
            if node.get("type") != "SELECTION" or node.get("selectionType") != "QUICKREPLY":
                continue

            node_id = node.get("id")
            node_name = node.get("name", "")
            node_type = node.get("type", "")
            module_type = node.get("selectionType", "")

            # payloads[*].text -> BUTTON/<payload_type>
            payloads = node.get("payloads", [])
            if isinstance(payloads, list):
                for p in payloads:
                    if not isinstance(p, dict):
                        continue
                    t = p.get("text")
                    if isinstance(t, str) and t.strip():
                        p_type = p.get("type", "")
                        source = f"BUTTON/{p_type}" if p_type else "BUTTON"
                        candidate = {
                            "node_id": node_id,
                            "node_name": node_name,
                            "node_type": node_type,
                            "module_type": module_type,
                            "source": source,
                            "text": t.strip(),
                        }
                        k = rowKey(candidate)
                        if k not in existing_keys:
                            w.writerow({"row_id": row_id, **candidate})
                            existing_keys.add(k)
                            row_id += 1
                            added += 1

            # prompt -> PROMPT
            t = node.get("prompt")
            if isinstance(t, str) and t.strip():
                candidate = {
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                    "module_type": module_type,
                    "source": "PROMPT",
                    "text": t.strip(),
                }
                k = rowKey(candidate)
                if k not in existing_keys:
                    w.writerow({"row_id": row_id, **candidate})
                    existing_keys.add(k)
                    row_id += 1
                    added += 1

            # errorMessage -> ERRORMESSAGE
            t = node.get("errorMessage")
            if isinstance(t, str) and t.strip():
                candidate = {
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                    "module_type": module_type,
                    "source": "ERRORMESSAGE",
                    "text": t.strip(),
                }
                k = rowKey(candidate)
                if k not in existing_keys:
                    w.writerow({"row_id": row_id, **candidate})
                    existing_keys.add(k)
                    row_id += 1
                    added += 1

    print(f"[send_selection_quickreply] {added} yeni satır eklendi.")


def send_selection_card(json_path, csv_path):
    """
    SELECTION/CARD:
      - payloads[*].buttons[*].text -> BUTTON/<type>
      - payloads[*].title           -> CARD/TITLE
      - payloads[*].subtitle        -> CARD/SUBTITLE
      - payloads[*].text            -> CARD/TEXT
      - errorMessage                -> ERRORMESSAGE
    Yalnızca yeni satırlar CSV'ye eklenir (tekilleştirme).
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    nodes = data["nodes"]

    ensureHeader(csv_path, FIELDNAMES)
    existing_keys = loadKeySet(csv_path)
    row_id = nextRowId(csv_path)

    added = 0
    with open(csv_path, "a", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=FIELDNAMES)

        for node in nodes.values():
            if node.get("type") != "SELECTION" or node.get("selectionType") != "CARD":
                continue

            node_id = node.get("id")
            node_name = node.get("name", "")
            node_type = node.get("type", "")
            module_type = node.get("selectionType", "")

            payloads = node.get("payloads", [])
            if isinstance(payloads, list):
                for item in payloads:
                    if not isinstance(item, dict):
                        continue

                    # BUTTON'lar
                    btns = item.get("buttons", [])
                    if isinstance(btns, list):
                        for b in btns:
                            if not isinstance(b, dict):
                                continue
                            bt = b.get("text")
                            if isinstance(bt, str) and bt.strip():
                                btype = b.get("type", "")
                                source = f"BUTTON/{btype}" if btype else "BUTTON"
                                candidate = {
                                    "node_id": node_id,
                                    "node_name": node_name,
                                    "node_type": node_type,
                                    "module_type": module_type,
                                    "source": source,
                                    "text": bt.strip(),
                                }
                                k = rowKey(candidate)
                                if k not in existing_keys:
                                    w.writerow({"row_id": row_id, **candidate})
                                    existing_keys.add(k)
                                    row_id += 1
                                    added += 1

                    # CARD alanları: title/subtitle/text
                    title = item.get("title")
                    if isinstance(title, str) and title.strip():
                        candidate = {
                            "node_id": node_id,
                            "node_name": node_name,
                            "node_type": node_type,
                            "module_type": module_type,
                            "source": "CARD/TITLE",
                            "text": title.strip(),
                        }
                        k = rowKey(candidate)
                        if k not in existing_keys:
                            w.writerow({"row_id": row_id, **candidate})
                            existing_keys.add(k)
                            row_id += 1
                            added += 1

                    subtitle = item.get("subtitle")
                    if isinstance(subtitle, str) and subtitle.strip():
                        candidate = {
                            "node_id": node_id,
                            "node_name": node_name,
                            "node_type": node_type,
                            "module_type": module_type,
                            "source": "CARD/SUBTITLE",
                            "text": subtitle.strip(),
                        }
                        k = rowKey(candidate)
                        if k not in existing_keys:
                            w.writerow({"row_id": row_id, **candidate})
                            existing_keys.add(k)
                            row_id += 1
                            added += 1

                    txt = item.get("text")
                    if isinstance(txt, str) and txt.strip():
                        candidate = {
                            "node_id": node_id,
                            "node_name": node_name,
                            "node_type": node_type,
                            "module_type": module_type,
                            "source": "CARD/TEXT",
                            "text": txt.strip(),
                        }
                        k = rowKey(candidate)
                        if k not in existing_keys:
                            w.writerow({"row_id": row_id, **candidate})
                            existing_keys.add(k)
                            row_id += 1
                            added += 1

            # errorMessage -> ERRORMESSAGE
            t = node.get("errorMessage")
            if isinstance(t, str) and t.strip():
                candidate = {
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                    "module_type": module_type,
                    "source": "ERRORMESSAGE",
                    "text": t.strip(),
                }
                k = rowKey(candidate)
                if k not in existing_keys:
                    w.writerow({"row_id": row_id, **candidate})
                    existing_keys.add(k)
                    row_id += 1
                    added += 1

    print(f"[send_selection_card] {added} yeni satır eklendi.")


def send_selection_list(json_path, csv_path):
    """
    SELECTION/LIST:
      - payloads[*].listSectionTitle                  -> LIST/SECTION/TITLE
      - payloads[*].listCardRow[*].listRowTitle       -> LIST/ROW/TITLE
      - payloads[*].listCardRow[*].listRowDescription -> LIST/ROW/DESCRIPTION
      - messageBoxOptionsButtonText (node/payload)    -> BUTTON/TEXT
      - messageBoxBody (node/payload)                 -> LIST/MESSAGE
      - listHeader (node/payload)                     -> LIST/HEADER
      - errorMessage (node)                           -> ERRORMESSAGE
    Yalnızca yeni satırlar CSV'ye eklenir (tekilleştirme).
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    nodes = data["nodes"]

    ensureHeader(csv_path, FIELDNAMES)
    existing_keys = loadKeySet(csv_path)
    row_id = nextRowId(csv_path)

    added = 0
    with open(csv_path, "a", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=FIELDNAMES)

        for node in nodes.values():
            if node.get("type") != "SELECTION" or node.get("selectionType") != "LIST":
                continue

            node_id = node.get("id")
            node_name = node.get("name", "")
            node_type = node.get("type", "")
            module_type = node.get("selectionType", "")

            # ---- Node-level alanlar ----
            mb_button = node.get("messageBoxOptionsButtonText")
            if isinstance(mb_button, str) and mb_button.strip():
                candidate = {
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                    "module_type": module_type,
                    "source": "BUTTON/TEXT",
                    "text": mb_button.strip(),
                }
                k = rowKey(candidate)
                if k not in existing_keys:
                    w.writerow({"row_id": row_id, **candidate})
                    existing_keys.add(k)
                    row_id += 1
                    added += 1

            mb_body = node.get("messageBoxBody")
            if isinstance(mb_body, str) and mb_body.strip():
                candidate = {
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                    "module_type": module_type,
                    "source": "LIST/MESSAGE",
                    "text": mb_body.strip(),
                }
                k = rowKey(candidate)
                if k not in existing_keys:
                    w.writerow({"row_id": row_id, **candidate})
                    existing_keys.add(k)
                    row_id += 1
                    added += 1

            list_header = node.get("listHeader")
            if isinstance(list_header, str) and list_header.strip():
                candidate = {
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                    "module_type": module_type,
                    "source": "LIST/HEADER",
                    "text": list_header.strip(),
                }
                k = rowKey(candidate)
                if k not in existing_keys:
                    w.writerow({"row_id": row_id, **candidate})
                    existing_keys.add(k)
                    row_id += 1
                    added += 1

            # ---- Payload-level alanlar ----
            payloads = node.get("payloads", [])
            if isinstance(payloads, list):
                for item in payloads:
                    if not isinstance(item, dict):
                        continue

                    section_title = item.get("listSectionTitle")
                    if isinstance(section_title, str) and section_title.strip():
                        candidate = {
                            "node_id": node_id,
                            "node_name": node_name,
                            "node_type": node_type,
                            "module_type": module_type,
                            "source": "LIST/SECTION/TITLE",
                            "text": section_title.strip(),
                        }
                        k = rowKey(candidate)
                        if k not in existing_keys:
                            w.writerow({"row_id": row_id, **candidate})
                            existing_keys.add(k)
                            row_id += 1
                            added += 1

                    rows_list = item.get("listCardRow")
                    if rows_list is None:
                        rows_list = item.get("lisrCardRow")  # olası yazım hatası
                    if isinstance(rows_list, list):
                        for r in rows_list:
                            if not isinstance(r, dict):
                                continue
                            row_title = r.get("listRowTitle")
                            if isinstance(row_title, str) and row_title.strip():
                                candidate = {
                                    "node_id": node_id,
                                    "node_name": node_name,
                                    "node_type": node_type,
                                    "module_type": module_type,
                                    "source": "LIST/ROW/TITLE",
                                    "text": row_title.strip(),
                                }
                                k = rowKey(candidate)
                                if k not in existing_keys:
                                    w.writerow({"row_id": row_id, **candidate})
                                    existing_keys.add(k)
                                    row_id += 1
                                    added += 1
                            row_desc = r.get("listRowDescription")
                            if isinstance(row_desc, str) and row_desc.strip():
                                candidate = {
                                    "node_id": node_id,
                                    "node_name": node_name,
                                    "node_type": node_type,
                                    "module_type": module_type,
                                    "source": "LIST/ROW/DESCRIPTION",
                                    "text": row_desc.strip(),
                                }
                                k = rowKey(candidate)
                                if k not in existing_keys:
                                    w.writerow({"row_id": row_id, **candidate})
                                    existing_keys.add(k)
                                    row_id += 1
                                    added += 1

                    # payload-level messageBoxOptionsButtonText
                    mb_button_p = item.get("messageBoxOptionsButtonText")
                    if isinstance(mb_button_p, str) and mb_button_p.strip():
                        candidate = {
                            "node_id": node_id,
                            "node_name": node_name,
                            "node_type": node_type,
                            "module_type": module_type,
                            "source": "BUTTON/TEXT",
                            "text": mb_button_p.strip(),
                        }
                        k = rowKey(candidate)
                        if k not in existing_keys:
                            w.writerow({"row_id": row_id, **candidate})
                            existing_keys.add(k)
                            row_id += 1
                            added += 1

                    # payload-level messageBoxBody
                    mb_body_p = item.get("messageBoxBody")
                    if isinstance(mb_body_p, str) and mb_body_p.strip():
                        candidate = {
                            "node_id": node_id,
                            "node_name": node_name,
                            "node_type": node_type,
                            "module_type": module_type,
                            "source": "LIST/MESSAGE",
                            "text": mb_body_p.strip(),
                        }
                        k = rowKey(candidate)
                        if k not in existing_keys:
                            w.writerow({"row_id": row_id, **candidate})
                            existing_keys.add(k)
                            row_id += 1
                            added += 1

                    # payload-level listHeader
                    list_header_p = item.get("listHeader")
                    if isinstance(list_header_p, str) and list_header_p.strip():
                        candidate = {
                            "node_id": node_id,
                            "node_name": node_name,
                            "node_type": node_type,
                            "module_type": module_type,
                            "source": "LIST/HEADER",
                            "text": list_header_p.strip(),
                        }
                        k = rowKey(candidate)
                        if k not in existing_keys:
                            w.writerow({"row_id": row_id, **candidate})
                            existing_keys.add(k)
                            row_id += 1
                            added += 1

            # ---- errorMessage -> ERRORMESSAGE ----
            err = node.get("errorMessage")
            if isinstance(err, str) and err.strip():
                candidate = {
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                    "module_type": module_type,
                    "source": "ERRORMESSAGE",
                    "text": err.strip(),
                }
                k = rowKey(candidate)
                if k not in existing_keys:
                    w.writerow({"row_id": row_id, **candidate})
                    existing_keys.add(k)
                    row_id += 1
                    added += 1

    print(f"[send_selection_list] {added} yeni satır eklendi.")
