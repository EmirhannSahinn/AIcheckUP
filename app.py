#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import shutil
import zipfile
import threading
import subprocess
import smtplib
import uuid
from email.message import EmailMessage
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import sys, logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("aicheckup")

from fastapi import Body
import smtplib

@app.get("/smtp-diagnose")
def smtp_diagnose():
    safe_env = {
        "SMTP_SERVER": os.getenv("SMTP_SERVER"),
        "SMTP_PORT": os.getenv("SMTP_PORT"),
        "SMTP_USER": os.getenv("SMTP_USER"),
        "FROM_EMAIL": os.getenv("FROM_EMAIL"),
        "SMTP_USE_SSL": os.getenv("SMTP_USE_SSL", "false"),
    }
    # şifreyi sızdırmayalım
    safe_env["SMTP_PASS"] = "****" if os.getenv("SMTP_PASS") else ""

    try:
        server = os.getenv("SMTP_SERVER", "")
        port   = int(os.getenv("SMTP_PORT", "587") or "587")
        use_ssl = str(os.getenv("SMTP_USE_SSL", "false")).lower() in {"1","true","yes","on"}

        if use_ssl:
            s = smtplib.SMTP_SSL(server, port, timeout=5); s.close()
        else:
            s = smtplib.SMTP(server, port, timeout=5); s.ehlo(); s.close()

        ok, msg = True, "Bağlantı kuruldu"
    except Exception as e:
        ok, msg = False, f"Bağlantı hatası: {e}"

    return {"ok": ok, "message": msg, "env": safe_env}

@app.post("/smtp-test")
def smtp_test(payload: dict = Body(...)):
    to = (payload or {}).get("to")
    if not to:
        return JSONResponse({"ok": False, "error": "to gerekli"}, status_code=400)
    try:
        send_email_with_attachment(to, "AIcheckUP SMTP test", "Merhaba! Bu bir testtir.", None)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

import tempfile
from fastapi.responses import JSONResponse

@app.get("/fs-diagnose")
def fs_diagnose():
    info = {
        "OUTPUTS_DIR": OUTPUTS_DIR,
        "BASE_DIR": BASE_DIR,
        "tmp": "/tmp",
        "results": {}
    }
    try:
        os.makedirs(OUTPUTS_DIR, exist_ok=True)
        test_dir = os.path.join(OUTPUTS_DIR, "fs_test")
        os.makedirs(test_dir, exist_ok=True)
        test_file = os.path.join(test_dir, "hello.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("hello from render\n")
        # zip denemesi
        test_zip = os.path.join(OUTPUTS_DIR, "fs_test.zip")
        with zipfile.ZipFile(test_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(test_file, arcname="hello.txt")
        size = os.path.getsize(test_zip)
        info["results"]["ok"] = True
        info["results"]["zip_path"] = test_zip
        info["results"]["zip_size"] = size
    except Exception as e:
        info["results"]["ok"] = False
        info["results"]["error"] = str(e)
    return JSONResponse(info)

# =========================
# Genel Ayarlar / Yollar
# =========================

#BASE_DIR      = os.path.dirname(os.path.abspath(__file__))

# proje kökü
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Render için varsayılanı /tmp yap; istersen ENV ile de geçebilirsin
OUTPUTS_DIR = os.getenv(
    "OUTPUTS_DIR",
    "/tmp/aicheckup-outputs" if os.getenv("RENDER") else os.path.join(BASE_DIR, "outputs")
)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

SCRIPT_NAME   = "spellcheck_16092025_0900.py"   # gerekirse değiştir
SCRIPT_PATH   = os.path.join(BASE_DIR, SCRIPT_NAME)
OUTPUTS_DIR   = os.path.join(BASE_DIR, "outputs")
STATIC_DIR    = os.path.join(BASE_DIR, "static")   # index.html burada


# .env'i otomatik yükle (BASE_DIR ve çalışma dizininde ara)
try:
    from dotenv import load_dotenv, find_dotenv
    # Önce ENV_FILE verilmişse onu, yoksa .env'i otomatik bul
    env_file = os.getenv("ENV_FILE") or find_dotenv(filename=".env", usecwd=True)
    if env_file:
        load_dotenv(env_file, override=True)
except Exception:
    pass


os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR,  exist_ok=True)


# UI'da kullandığımız etiket isimleri
SECTION_TAGS = ("spellcheck", "grammar", "punctuation", "clarity", "tone")

# =========================
# SMTP (ENV'den okunur)
# =========================
SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "587") or "587")
SMTP_USER   = os.getenv("SMTP_USER", "")
SMTP_PASS   = os.getenv("SMTP_PASS", "")
FROM_EMAIL  = os.getenv("FROM_EMAIL", SMTP_USER or "")

def smtp_config_ok() -> bool:
    return all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS, FROM_EMAIL])

def _missing_smtp_fields():
    missing = []
    if not SMTP_SERVER: missing.append("SMTP_SERVER")
    if not SMTP_PORT:   missing.append("SMTP_PORT")
    if not SMTP_USER:   missing.append("SMTP_USER")
    if not SMTP_PASS:   missing.append("SMTP_PASS")
    if not FROM_EMAIL:  missing.append("FROM_EMAIL")
    return missing
# =========================
# FastAPI App
# =========================
app = FastAPI(title="AIcheckUP FastAPI")

# CORS serbest
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# Static (UI)
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# =========================
# Paylaşılan Durum
# =========================
LOCK = threading.RLock()
RUNS = {}  # run_id -> dict

# =========================
# Yardımcılar
# =========================

def is_truthy(val) -> bool:
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in {"1", "true", "yes", "y", "on", "evet"}

def zip_dir(src_dir: str, zip_path: str):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, src_dir)
                zf.write(full, arcname=rel)

def send_email_with_attachment(to_email: str, subject: str, body: str, attachment_path: Optional[str]):
    if not smtp_config_ok():
        raise RuntimeError("SMTP yapılandırması eksik (SMTP_* ENV).")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.set_content(body)

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            data = f.read()
        filename = os.path.basename(attachment_path)
        msg.add_attachment(data, maintype="application", subtype="octet-stream", filename=filename)

    use_ssl = str(os.getenv("SMTP_USE_SSL", "false")).strip().lower() in {"1","true","yes","on"}
    server = SMTP_SERVER
    port   = int(os.getenv("SMTP_PORT", "587") or "587")

    logger.info("SMTP: connect %s:%s (ssl=%s) user=%s", server, port, use_ssl, SMTP_USER)

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(server, port, timeout=20) as smtp:
                smtp.login(SMTP_USER, SMTP_PASS)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(server, port, timeout=20) as smtp:
                smtp.ehlo()
                try:
                    smtp.starttls()
                except Exception as e:
                    logger.warning("SMTP: STARTTLS başarısız/atlandı: %s", e)
                smtp.login(SMTP_USER, SMTP_PASS)
                smtp.send_message(msg)

        logger.info("SMTP: mail gönderildi -> %s", to_email)

    except Exception as e:
        logger.exception("SMTP: gönderim hatası")
        raise


def _log_footer(status_text: str, last_file: Optional[str], zip_path: Optional[str], duration_sec: float) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "",
        "============================================================",
        f"🏁 Program bitti | Durum: {status_text} | Zaman: {now}",
        f"Süre: {_fmt_duration(duration_sec)}"
    ]
    if last_file:
        lines.append(f"Son dosya: {last_file}")
    if zip_path:
        lines.append(f"ZIP: {zip_path}")
        # zip oluşturulduktan sonra:
        with LOCK:
            RUNS[run_id]["log"] += f"\n🗜️ ZIP hazır: {zip_path} ({os.path.getsize(zip_path)} bayt)\n"
    if not zip_path or not os.path.exists(zip_path):
        with LOCK:
            RUNS[run_id]["log"] += "\nℹ️ E-posta eki bulunamadı; sadece linkler gönderilecek.\n"

    lines.append("============================================================\n")
    return "\n".join(lines)

def _normalize_line(raw: str) -> str:
    """Stdout'u kayıpsız döndür; sadece satır başlangıcına kaçan tag'leri kır."""
    s = raw.replace("\r\n", "\n")
    if not s.endswith("\n"):
        s += "\n"
    for tag in SECTION_TAGS:
        s = re.sub(rf'(?<!\n)\[{tag}\]', f'\n[{tag}]', s)
    return s

def _auto_close_sections(run_id: str, text: str) -> str:
    """Yeni etiket gelmeden önceki etiket kapanmadıysa '[tag] Bitti.' ekle."""
    st = RUNS[run_id].setdefault("_sec", {"open": None, "closed": set()})
    out_lines = []

    for rawln in text.splitlines(True):  # satır sonu korunur
        ln = rawln

        m = re.match(r'^\[(\w+)\]\s*(.*)', ln)
        if m:
            tag = m.group(1)
            rest = m.group(2)
            if tag in SECTION_TAGS:
                # önceki açık bölüm kapanmadıysa, kapat
                if st["open"] and st["open"] != tag and st["open"] not in st["closed"]:
                    out_lines.append(f"[{st['open']}] Bitti.\n")
                    st["closed"].add(st["open"])

                # bu satır mevcut tag için Bitti mi?
                if rest.strip().lower().startswith("bitti"):
                    st["closed"].add(tag)
                    if st["open"] == tag:
                        st["open"] = None
                else:
                    st["open"] = tag

        out_lines.append(ln if ln.endswith("\n") else ln + "\n")

    return "".join(out_lines)



def _email_partial(run_id: str, reason_text: str):
    """ZIP'i e-postala (varsa). Yalnızca bir kez dener."""
    base_url = os.getenv("PUBLIC_BASE_URL", "")  # Render ENV: PUBLIC_BASE_URL=https://aicheckup.onrender.com
    download_zip_url  = f"{base_url}/download/{run_id}" if base_url else ""
    download_last_url = f"{base_url}/download-last/{run_id}" if base_url else ""

    with LOCK:
        r = RUNS.get(run_id)
        if not r or r.get("email_sent"):
            return
        email_to = (r.get("email_to") or "").strip()
        zip_path = r.get("zip")
        tone = r.get("tone", "")
        outdir = r.get("outdir")
        status = r.get("status")
        t0 = r.get("t0", time.perf_counter())
        duration = _fmt_duration(time.perf_counter() - t0)

    # Bilgilendirici atlama logları
    if not email_to:
        with LOCK:
            RUNS[run_id]["log"] += "\nℹ️ E-posta atlanıyor: alıcı girilmemiş.\n"
        return
    if not smtp_config_ok():
        miss = _missing_smtp_fields()
        with LOCK:
            RUNS[run_id]["log"] += (
                f"\nℹ️ E-posta atlanıyor: SMTP yapılandırması eksik "
                f"({', '.join(miss)}).\n"
            )
        return

    subject = f"AIcheckUP çıktısı ({status}) - {run_id}"
    body = (
        f"Merhaba,\n\n"
        f"Çalışma {reason_text}.\n"
        f"run_id: {run_id}\n"
        f"TARGET_TONE: {tone}\n"
        f"Çıktı klasörü: {outdir}\n"
        f"Süre: {duration}\n"
        f"{'ZIP eklendi.' if zip_path else 'ZIP eklenemedi veya bulunamadı.'}\n"
        f"{('ZIP indir: ' + download_zip_url + '\\n') if download_zip_url else ''}"
        f"{('Son dosyayı indir: ' + download_last_url + '\\n') if download_last_url else ''}\n"
        f"Sevgiler."
    )
    try:
        send_email_with_attachment(email_to, subject, body, zip_path)
        with LOCK:
            RUNS[run_id]["email_sent"] = True
            RUNS[run_id]["log"] += f"\n📧 E-posta gönderildi: {email_to}\n"
    except Exception as e:
        with LOCK:
            RUNS[run_id]["log"] += f"\n⚠️ E-posta gönderilemedi: {e}\n"

# =========================
# Çalıştırma
# =========================

def start_run(json_path: str, target_tone: str, email_to: Optional[str]) -> str:
    # --- benzersiz run_id ---
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    rid = uuid.uuid4().hex[:6]
    run_id = f"run_{ts}_{rid}"

    outdir = os.path.join(OUTPUTS_DIR, run_id)
    os.makedirs(outdir, exist_ok=True)

    # Çıktı dosyaları
    output_csv_path   = os.path.join(outdir, "result.csv")
    messages_csv_path = os.path.join(outdir, "messages.csv")

    # Başlangıç logu
    with LOCK:
        RUNS[run_id] = {
            "outdir": outdir,
            "zip": None,
            "log": (
                "🚀 Başlatıldı\n"
                f"TARGET_TONE={target_tone}\n"
                f"JSON: {json_path}\n"
                f"OUTPUT_CSV: {output_csv_path}\n"
                f"MESSAGES_CSV: {messages_csv_path}\n"
            ),
            "status": "running",
            "code": None,
            "last_file": None,
            "email_to": email_to,
            "tone": target_tone,
            "stopped": False,
            "email_sent": False,
            "proc": None,
            "_sec": {"open": None, "closed": set()},
            "t0": time.perf_counter(),
        }
        RUNS[run_id]["log"] += "\n"

    # Komut
    cmd = [
        "python", "-u", SCRIPT_PATH,
        "--json", json_path,
        "--output_csv", output_csv_path,
        "--messages_csv", messages_csv_path,
        "--target_tone", target_tone,
    ]

    def worker():
        try:
            with LOCK:
                RUNS[run_id]["log"] += f"Komut: {' '.join(cmd)}\n\n"

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            with LOCK:
                RUNS[run_id]["proc"] = proc

            # satır kaçırmaya dayanıklı okuma
            while True:
                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        tail = proc.stdout.read() or ""
                        if tail:
                            tail = _auto_close_sections(run_id, _normalize_line(tail))
                            with LOCK:
                                prefix = "" if RUNS[run_id]["log"].endswith("\n") else "\n"
                                RUNS[run_id]["log"] += prefix + tail
                        break
                    time.sleep(0.01)
                    continue

                line = _auto_close_sections(run_id, _normalize_line(line))
                with LOCK:
                    prefix = "" if RUNS[run_id]["log"].endswith("\n") else "\n"
                    RUNS[run_id]["log"] += prefix + line

            code = proc.wait()

            # Üretilen dosyalar
            produced = []
            for root, _, files in os.walk(outdir):
                for f in files:
                    produced.append(os.path.join(root, f))
            last_file = max(produced, key=os.path.getmtime) if produced else None
            zip_path = None
            if produced:
                zip_path = os.path.join(OUTPUTS_DIR, f"{run_id}.zip")
                zip_dir(outdir, zip_path)

            # Açık kalan bölüm varsa kapat
            with LOCK:
                st = RUNS[run_id].setdefault("_sec", {"open": None, "closed": set()})
                if st["open"] and st["open"] not in st["closed"]:
                    RUNS[run_id]["log"] += f"\n[{st['open']}] Bitti.\n"
                    st["closed"].add(st["open"])
                st["open"] = None

            # Durum
            with LOCK:
                RUNS[run_id]["code"] = code
                RUNS[run_id]["last_file"] = last_file
                if zip_path:
                    RUNS[run_id]["zip"] = zip_path
                t0 = RUNS[run_id]["t0"]
            duration = time.perf_counter() - t0

            if code == 0:
                with LOCK:
                    RUNS[run_id]["status"] = "ok"
                    RUNS[run_id]["log"] += _log_footer("Başarı", last_file, zip_path, duration)
                _email_partial(run_id, "başarıyla tamamlandı")
            else:
                with LOCK:
                    was_stopped = RUNS[run_id]["stopped"]
                if was_stopped:
                    with LOCK:
                        RUNS[run_id]["status"] = "stopped"
                        RUNS[run_id]["log"] += _log_footer("Durduruldu", last_file, zip_path, duration)
                    _email_partial(run_id, "kullanıcı durdurdu")
                else:
                    with LOCK:
                        RUNS[run_id]["status"] = "error"
                        RUNS[run_id]["log"] += _log_footer("Hata", last_file, zip_path, duration)
                    _email_partial(run_id, "yarıda kesildi")

        except Exception as e:
            with LOCK:
                RUNS[run_id]["status"] = "error"
                t0 = RUNS[run_id].get("t0", time.perf_counter())
                duration = time.perf_counter() - t0
                RUNS[run_id]["log"] += f"\n❌ İstisna: {e}\n" + _log_footer("Hata", None, None, duration)
            _email_partial(run_id, "yarıda kesildi")

    threading.Thread(target=worker, daemon=True).start()
    return run_id

# =========================
# HTTP Endpoints
# =========================

@app.get("/", response_class=HTMLResponse)
def home():
    index = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index):
        with open(index, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>AIcheckUP</h1><p>UI için static/index.html yükleyin.</p>")

@app.post("/run")
async def run_local(payload: dict):
    input_mode   = (payload.get("input_mode") or "").lower()
    json_path    = payload.get("json_path") or ""
    target_tone  = payload.get("target_tone") or ""
    email_enabled= is_truthy(payload.get("email_enabled"))
    email_to     = (payload.get("email_to") or "").strip()
    if input_mode != "local":
        return JSONResponse({"error": "input_mode=local bekleniyor"}, status_code=400)
    if not json_path or not os.path.exists(json_path):
        return JSONResponse({"error": "Geçersiz JSON yolu"}, status_code=400)
    if not target_tone:
        return JSONResponse({"error": "TARGET_TONE boş olamaz"}, status_code=400)
    run_id = start_run(json_path, target_tone, email_to if (email_enabled and email_to) else None)
    return {"run_id": run_id}

@app.post("/run-upload")
async def run_upload(
    file_json: UploadFile = File(...),
    target_tone: str = Form(...),
    email_enabled: str = Form("false"),
    email_to: str = Form(""),
):
    # Yüklenen JSON'u outputs altına al
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp_dir = os.path.join(OUTPUTS_DIR, f"uploaded_{ts}")
    os.makedirs(tmp_dir, exist_ok=True)
    json_dest = os.path.join(tmp_dir, file_json.filename)
    with open(json_dest, "wb") as f:
        shutil.copyfileobj(file_json.file, f)

    enabled = is_truthy(email_enabled)
    to_addr = (email_to or "").strip()
    run_id = start_run(json_dest, target_tone, to_addr if (enabled and to_addr) else None)
    return {"run_id": run_id}

@app.get("/stream/{run_id}")
def stream(run_id: str):
    if run_id not in RUNS:
        return JSONResponse({"error": "run_id bulunamadı"}, status_code=404)

    def event_gen():
        last_len = 0
        # ilk chunk: o ana kadarki log
        with LOCK:
            data = RUNS[run_id]["log"]
        yield f"data: {data}\n\n"
        last_len = len(data)

        while True:
            time.sleep(0.25)
            with LOCK:
                r = RUNS.get(run_id)
                if not r:
                    break
                buf = r["log"]
                status = r["status"]
            if len(buf) > last_len:
                chunk = buf[last_len:]
                last_len = len(buf)
                for part in chunk.splitlines(True):
                    yield f"data: {part}\n\n"

            if status in ("ok", "error", "stopped"):
                break

    return StreamingResponse(event_gen(), media_type="text/event-stream")

@app.get("/status/{run_id}")
def status(run_id: str):
    with LOCK:
        r = RUNS.get(run_id)
        if not r:
            return JSONResponse({"error": "run_id bulunamadı"}, status_code=404)
        payload = {
            "status": r["status"],
            "zip": bool(r.get("zip")),
            "last_file": bool(r.get("last_file")),
        }
    return payload

@app.get("/download/{run_id}")
def download_zip(run_id: str):
    with LOCK:
        r = RUNS.get(run_id)
        if not r or not r.get("zip") or not os.path.exists(r["zip"]):
            return JSONResponse({"error": "ZIP yok"}, status_code=404)
        path = r["zip"]
    return FileResponse(path, filename=os.path.basename(path))

@app.get("/download-last/{run_id}")
def download_last(run_id: str):
    with LOCK:
        r = RUNS.get(run_id)
        if not r or not r.get("last_file") or not os.path.exists(r["last_file"]):
            return JSONResponse({"error": "Dosya yok"}, status_code=404)
        path = r["last_file"]
    return FileResponse(path, filename=os.path.basename(path))

@app.post("/stop/{run_id}")
def stop(run_id: str):
    with LOCK:
        r = RUNS.get(run_id)
        if not r:
            return JSONResponse({"error": "run_id bulunamadı"}, status_code=404)
        r["stopped"] = True
        proc = r.get("proc")
    try:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
    except Exception:
        pass
    return {"ok": True}

# Basit logo fallback
@app.get("/logo")
def logo_fallback():
    from io import BytesIO
    import base64
    png_1x1 = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    bio = BytesIO(png_1x1)
    return StreamingResponse(bio, media_type="image/png")

# =========================
# Main
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
