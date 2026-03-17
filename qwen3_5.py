from io import BytesIO
import time
import requests
import os
import ollama  # Library Ollama
from dotenv import load_dotenv
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import csv
from datetime import datetime
import re

from prompts import (
    FEWSHOT_CAPTIONS,
    DESCRIBE_IMAGE_PROMPT,
    GENERATE_FINAL_CAPTION_PROMPT,
    GENERATE_ZEROSHOT_CAPTION_PROMPT,
    DEFAULT_LANGUAGE
)

# ====== LOAD ENV VARS ======
load_dotenv()

# Path dasar project (lokasi file ini)
BASE_DIR = os.path.dirname(__file__)

# ====== KONFIGURASI API MEME LOKAL ======
# Contoh: Flask di routes/meme.py jalan di localhost:5000
MEME_API_BASE   = os.getenv("MEME_API_BASE", "http://127.0.0.1:5000")

# ====== KONFIGURASI OLLAMA ======
# Default ke host server, bisa override via environment variable.
OLLAMA_HOST     = os.getenv("OLLAMA_HOST", "http://152.42.226.64:11434")

# ====== KONFIGURASI CLIP SCORE ======
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
try:
    clip_model = CLIPModel.from_pretrained(CLIP_MODEL_NAME)
    clip_processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    clip_model = clip_model.to(device)
    print(f"[CLIP] Model loaded on device: {device}")
except Exception as e:
    print(f"[CLIP Warning] Failed to load CLIP model: {e}")
    clip_model = None
    clip_processor = None

# MODEL KONFIGURASI
# Prioritas env var khusus Qwen3.5; tetap support fallback legacy LLAMA4_* untuk kompatibilitas.
MODEL_VLM       = os.getenv("QWEN3_5_MODEL_VLM", os.getenv("LLAMA4_MODEL_VLM", "qwen3.5:latest"))
MODEL_LLM       = os.getenv("QWEN3_5_MODEL_LLM", os.getenv("LLAMA4_MODEL_LLM", "qwen3.5:latest"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# Endpoint API lokal
MEME_API_GET    = f"{MEME_API_BASE}/get_memes"
MEME_API_CAPTION= f"{MEME_API_BASE}/caption-image"
HTTP_TIMEOUT    = 20

# ====== CSV LOGGING ======
RESULTS_CSV_PATH = os.path.join(BASE_DIR, "meme_generation_results.csv")
CSV_COLUMNS = ["run_id", "timestamp", "template_id", "method", "language", "model", "temperature", "topic", "caption", "meme_url", "clip_score", "crossmodal_incongruity", "run_time_seconds"]

def initialize_csv():
    """Inisialisasi CSV dan upgrade schema jika perlu."""
    if not os.path.exists(RESULTS_CSV_PATH):
        with open(RESULTS_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
        print(f"[CSV] Created: {RESULTS_CSV_PATH}")
        return

    # Upgrade file lama: tambahkan kolom baru agar tetap kebaca rapi di Excel.
    with open(RESULTS_CSV_PATH, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        existing_columns = reader.fieldnames or []
        if "run_time_seconds" in existing_columns:
            return
        rows = list(reader)

    with open(RESULTS_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})
    print(f"[CSV] Upgraded schema with 'run_time_seconds': {RESULTS_CSV_PATH}")

def get_next_run_id():
    """Ambil run_id berikutnya (auto-increment)"""
    if not os.path.exists(RESULTS_CSV_PATH):
        return 1
    
    try:
        with open(RESULTS_CSV_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) <= 1:  # Hanya header
                return 1
            return int(lines[-1].split(',')[0]) + 1
    except Exception as e:
        print(f"[CSV Error] {e}")
        return 1

def save_result_to_csv(template_id, method, language, topic, caption, meme_url, clip_score, incongruity_score, model, temperature, run_time_seconds=None):
    """Simpan result ke CSV"""
    try:
        initialize_csv()
        run_id = get_next_run_id()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(RESULTS_CSV_PATH, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writerow({
                "run_id": run_id,
                "timestamp": timestamp,
                "template_id": template_id,
                "method": method,
                "language": language,
                "model": model,
                "temperature": temperature,
                "topic": topic,
                "caption": caption,
                "meme_url": meme_url,
                "clip_score": clip_score if clip_score is not None else "",
                "crossmodal_incongruity": incongruity_score if incongruity_score is not None else "",
                "run_time_seconds": run_time_seconds if run_time_seconds is not None else ""
            })
        print(f"[CSV] Saved result (run_id={run_id})")
        return run_id
    except Exception as e:
        print(f"[CSV Error] Failed to save: {e}")
        return None

# ====== HTTP SESSION ======
def make_session():
    s = requests.Session()
    retries = Retry(
        total=3, backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://",  HTTPAdapter(max_retries=retries))
    return s

session = make_session()
# Inisialisasi Client Ollama
client  = ollama.Client(host=OLLAMA_HOST)

# Memory ringan antar-run dalam satu proses untuk mengurangi caption sentris.
RECENT_CAPTIONS_BY_TOPIC = {}


def _normalize_single_box_caption(text):
    txt = " ".join(str(text or "").split()).strip()
    if not txt:
        return ""

    label_pattern = r"(?:[A-Za-zÀ-ÖØ-öø-ÿ][\wÀ-ÖØ-öø-ÿ-]{0,20}(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ][\wÀ-ÖØ-öø-ÿ-]{0,20}){0,2})\s*:\s*"
    txt = re.sub(label_pattern, "", txt).strip()
    txt = " ".join(txt.split())

    # Keep aligned with prompt constraints and avoid over-trimming.
    max_words = 8
    min_words_preferred = 3
    dangling_words = {
        "dan", "atau", "tapi", "yang", "karena", "jadi", "untuk", "dengan",
        "di", "ke", "dari", "pada", "saat", "ketika", "if", "and", "or",
        "but", "because", "so", "to", "with", "in", "on", "at", "of", "for"
    }

    def clean_ending(fragment):
        fragment = fragment.strip(" ,;:-")
        parts = fragment.split()
        while parts and parts[-1].lower() in dangling_words:
            parts.pop()
        return " ".join(parts).strip(" ,;:-")

    if not txt:
        return ""

    sentence_candidates = [clean_ending(s) for s in re.split(r"[.!?]+", txt) if s.strip()]
    valid_sentence_candidates = [
        c for c in sentence_candidates if 1 <= len(c.split()) <= max_words
    ]
    preferred_sentence_candidates = [
        c for c in valid_sentence_candidates if len(c.split()) >= min_words_preferred
    ]
    if preferred_sentence_candidates:
        return max(preferred_sentence_candidates, key=lambda c: len(c.split()))
    if valid_sentence_candidates:
        return max(valid_sentence_candidates, key=lambda c: len(c.split()))

    clause_candidates = [clean_ending(s) for s in re.split(r"[,;—-]+", txt) if s.strip()]
    valid_clause_candidates = [
        c for c in clause_candidates if 1 <= len(c.split()) <= max_words
    ]
    preferred_clause_candidates = [
        c for c in valid_clause_candidates if len(c.split()) >= min_words_preferred
    ]
    if preferred_clause_candidates:
        return max(preferred_clause_candidates, key=lambda c: len(c.split()))
    if valid_clause_candidates:
        return max(valid_clause_candidates, key=lambda c: len(c.split()))

    words = txt.split()
    fallback = clean_ending(" ".join(words[:max_words]))
    return fallback if fallback else " ".join(words[:max_words])


def _normalize_for_compare(text):
    txt = str(text or "").lower().strip()
    txt = re.sub(r"[^a-z0-9\s]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _is_caption_too_similar(candidate, recent_captions):
    """Cek apakah caption terlalu mirip dengan history terbaru."""
    cand_norm = _normalize_for_compare(candidate)
    if not cand_norm:
        return False

    cand_tokens = set(cand_norm.split())
    if not cand_tokens:
        return False

    for prev in recent_captions:
        prev_norm = _normalize_for_compare(prev)
        if not prev_norm:
            continue

        if cand_norm == prev_norm:
            return True

        prev_tokens = set(prev_norm.split())
        if not prev_tokens:
            continue

        overlap = len(cand_tokens & prev_tokens) / max(1, len(cand_tokens | prev_tokens))
        if overlap >= 0.5:
            return True

    return False


def _extract_visual_anchor(description):
    """Ambil kata kunci visual dari deskripsi gambar agar caption lebih nempel ke template."""
    txt = str(description or "").lower()
    keyword_groups = [
        ["kermit", "drake", "patrick", "spongebob", "jerry", "flork"],
        ["panik", "bingung", "pasrah", "senyum", "nangis", "ketawa", "kaget", "marah"],
        ["laptop", "hp", "papan", "rumus", "kelas", "kursi", "chat", "notif"],
    ]

    for group in keyword_groups:
        for kw in group:
            if kw in txt:
                return kw

    tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", txt) if len(t) >= 4]
    return tokens[0] if tokens else "ekspresi"


def _caption_mentions_anchor(caption, anchor):
    cap_norm = _normalize_for_compare(caption)
    anc_norm = _normalize_for_compare(anchor)
    if not cap_norm or not anc_norm:
        return True
    return anc_norm in cap_norm

# ============================================================
# CALCULATE CLIP SCORE
# ============================================================
def calculate_clip_score(image_path_or_url, caption):
    """
    Hitung CLIP score menggunakan cosine similarity antara image dan text embeddings.
    Score adalah cosine similarity yang berkisar [-1, 1].
    
    Args:
        image_path_or_url: Path/URL gambar meme
        caption: Caption teks untuk meme
    
    Returns:
        Float score ([-1, 1]), atau None jika CLIP model tidak tersedia
        - 1.0  : Perfect alignment
        - 0.0  : Orthogonal (no correlation)
        - -1.0 : Perfect anti-alignment
    """
    if clip_model is None or clip_processor is None:
        print(f"[CLIP Warning] Model not loaded (clip_model={clip_model is not None}, processor={clip_processor is not None})")
        return None
    
    try:
        print(f"[CLIP] Processing: {image_path_or_url[:50]}... | Caption: {caption[:30]}...")

        # Load gambar
        if image_path_or_url.startswith("http://") or image_path_or_url.startswith("https://"):
            print(f"[CLIP] Loading from URL: {image_path_or_url}")
            img_resp = session.get(image_path_or_url, timeout=HTTP_TIMEOUT)
            img_resp.raise_for_status()
            image = Image.open(BytesIO(img_resp.content)).convert("RGB")
        else:
            rel_path = image_path_or_url.lstrip("/")
            full_path = os.path.join(BASE_DIR, rel_path)
            print(f"[CLIP] Loading from file: {full_path}")
            if not os.path.exists(full_path):
                print(f"[CLIP Warning] File not found: {full_path}")
                return None
            image = Image.open(full_path).convert("RGB")

        # Preprocess separately for image and text to avoid sending text tensors to image fn
        image_inputs = clip_processor(images=image, return_tensors="pt")
        text_inputs = clip_processor(text=[caption], return_tensors="pt", padding=True)

        # Move tensors to device
        image_inputs = {k: v.to(device) for k, v in image_inputs.items()}
        text_inputs = {k: v.to(device) for k, v in text_inputs.items()}

        # Forward pass - Calculate cosine similarity between image and text embeddings
        with torch.no_grad():
            image_embeds = clip_model.get_image_features(**image_inputs)
            text_embeds = clip_model.get_text_features(**text_inputs)

            # Normalize embeddings
            image_embeds = image_embeds / image_embeds.norm(dim=-1, keepdim=True)
            text_embeds = text_embeds / text_embeds.norm(dim=-1, keepdim=True)

            # Cosine similarity (range: [-1, 1])
            similarity = (image_embeds * text_embeds).sum(dim=-1)
            score = similarity.item()

        print(f"[CLIP] Score: {score}")
        return round(score, 4)
    except Exception as e:
        print(f"[CLIP Error] {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================
# CALCULATE CROSS-MODAL INCONGRUITY
# ============================================================
def calculate_crossmodal_incongruity(clip_score):
    """
    Cross-modal incongruity diturunkan dari CLIP similarity.
    Nilai tinggi = teks dan gambar semakin tidak literal.
    """
    if clip_score is None:
        return None

    clip_norm = (clip_score + 1) / 2
    incongruity = 1 - clip_norm
    return round(incongruity, 4)


# ============================================================
# GET MEME TEMPLATE (via API lokal /get_memes)
# ============================================================
def get_meme_template(template_id):
    try:
        r = session.get(MEME_API_GET, timeout=HTTP_TIMEOUT)
        data = r.json()
        if not data.get("success"):
            return None
        for m in data["data"]["memes"]:
            if str(m["id"]) == str(template_id):
                return m
        return None
    except Exception as e:
        print(f"[Get Template Error] {e}")
        return None

# ============================================================
# VLM — DESCRIBE IMAGE (MENGGUNAKAN OLLAMA/LLaVA)
# ============================================================
def describe_image_with_ollama(path_or_url, language=None):
    """
    Menerima:
    - URL penuh (http/https), atau
    - path lokal relatif dari root project (mis: cleanmeme/pisau-pisau.jpg atau /cleanmeme/...)
    """
    if language is None:
        language = DEFAULT_LANGUAGE
    
    print(f"   (VLM: Menganalisa gambar dengan {MODEL_VLM}...)")
    try:
        # 1. Ambil bytes gambar, bisa dari URL atau file lokal
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            img_resp = session.get(path_or_url, timeout=HTTP_TIMEOUT)
            img_resp.raise_for_status()
            image_bytes = img_resp.content
        else:
            rel_path = path_or_url.lstrip("/")
            full_path = os.path.join(BASE_DIR, rel_path)
            with open(full_path, "rb") as f:
                image_bytes = f.read()

        prompt = DESCRIBE_IMAGE_PROMPT.get(language, DESCRIBE_IMAGE_PROMPT["id"])

        # 2. Kirim ke Ollama
        resp = client.chat(
            model=MODEL_VLM,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_bytes]  # Ollama menerima list by tes
            }]
        )

        return resp['message']['content']
    except Exception as e:
        err = str(e)
        err_lower = err.lower()

        if "403" in err or "forbidden" in err_lower:
            return (
                f"[VLM Error] Akses ke Ollama API ditolak (403) di '{OLLAMA_HOST}'. "
                "Endpoint '/lab' adalah UI Jupyter, bukan API Ollama. "
                "Gunakan host API Ollama langsung (contoh: http://<server-ip>:11434) "
                "dan pastikan port/API diizinkan dari client ini."
            )

        if "404" in err or "not found" in err_lower:
            return (
                f"[VLM Error] Model '{MODEL_VLM}' tidak ditemukan di host '{OLLAMA_HOST}'. "
                f"Jalankan di server: ollama pull {MODEL_VLM}"
            )

        return f"[VLM Error] {err} (host={OLLAMA_HOST}, model={MODEL_VLM})"

# ============================================================
# FEW-SHOT FINAL CAPTION (LLM: LLAMA) — pakai contoh dari prompts.py
# ============================================================
def generate_final_caption(description, topic, box_count=2, topic_key=None, language=None):
    """
    Generate caption final dengan few-shot dari prompts.py.
    - box_count == 1  -> satu caption (tanpa '||')
    - box_count >= 2  -> N caption dalam satu baris: cap1 || cap2 || ... || capN
    """
    if language is None:
        language = DEFAULT_LANGUAGE
    
    topic_data = (FEWSHOT_CAPTIONS.get(topic_key or "thesis") or FEWSHOT_CAPTIONS["thesis"]).get(language, {})
    format_key = "single" if box_count == 1 else "multi"
    fewshots_raw = topic_data.get(format_key, [])

    if box_count == 1:
        # Format: "Template: <desc>\nCaption: <cap tanpa ||>"
        fewshot_block = "\n\n".join(
            f'Template: {item.get("description", "-")}\nCaption: {item.get("caption", "").strip()}'
            for item in fewshots_raw if item.get("caption", "").strip()
        )
        prompt_template = GENERATE_FINAL_CAPTION_PROMPT.get(language, GENERATE_FINAL_CAPTION_PROMPT["id"])
        prompt = prompt_template["single_box"].format(
            description=description,
            topic=topic,
            fewshot_block=fewshot_block
        )
    else:
        # Format: "Template: <desc>\nCaption: <cap dengan ||>"
        fewshot_block = "\n\n".join(
            f'Template: {item.get("description", "-")}\nCaption: {item.get("caption", "")}'
            for item in fewshots_raw if item.get("caption", "").strip()
        )
        prompt_template = GENERATE_FINAL_CAPTION_PROMPT.get(language, GENERATE_FINAL_CAPTION_PROMPT["id"])
        prompt = prompt_template["multi_box"].format(
            description=description,
            topic=topic,
            box_count=box_count,
            fewshot_block=fewshot_block
        )

    try:
        resp = client.chat(
            model=MODEL_LLM,
            messages=[{'role': 'user', 'content': prompt}],
            options={
                "temperature": LLM_TEMPERATURE,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            }
        )
        txt = resp['message']['content'].replace("\n", " ").strip()
        txt = txt.replace('"', '').replace("'", "").strip()

        if box_count == 1:
            txt = _normalize_single_box_caption(txt)
            return txt if txt else "caption gagal"

        # Multi-box: pastikan jumlah segmen sesuai box_count
        parts = [p.strip() for p in txt.split("||") if p.strip()]
        if not parts:
            return " || ".join(["caption"] * box_count)

        # Jika kurang dari box_count, duplikasi segmen terakhir
        while len(parts) < box_count:
            parts.append(parts[-1])

        return " || ".join(parts[:box_count])
    except Exception as e:
        print(f"[Final Gen Error] {e}")
        return " || ".join(["Server Error"] * max(1, box_count))

# ============================================================
# ZERO-SHOT (LLM: LLAMA)
# ============================================================
def generate_zeroshot_caption(description, topic, box_count=2, language=None):
    """
    Zero-shot caption:
    - box_count == 1  -> satu caption (tanpa '||')
    - box_count >= 2  -> N caption dalam satu baris: cap1 || cap2 || ... || capN
    """
    if language is None:
        language = DEFAULT_LANGUAGE
    
    prompt_template = GENERATE_ZEROSHOT_CAPTION_PROMPT.get(language, GENERATE_ZEROSHOT_CAPTION_PROMPT["id"])
    
    if box_count == 1:
        prompt = prompt_template["single_box"].format(
            topic=topic,
            description=description
        )
    else:
        prompt = prompt_template["multi_box"].format(
            box_count=box_count,
            topic=topic,
            description=description
        )

    try:
        resp = client.chat(
            model=MODEL_LLM,
            messages=[{'role': 'user', 'content': prompt}],
            options={
                "temperature": LLM_TEMPERATURE,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            }
        )
        txt = resp['message']['content'].replace("\n", " ").strip()
        txt = txt.replace('"', '').replace("'", "").strip()

        if box_count == 1:
            txt = _normalize_single_box_caption(txt)
            return txt if txt else "caption gagal"

        # Multi-box: pecah berdasarkan '||' dan pastikan jumlah segmen
        parts = [p.strip() for p in txt.split("||") if p.strip()]
        if not parts:
            return " || ".join(["caption"] * box_count)

        while len(parts) < box_count:
            parts.append(parts[-1])

        return " || ".join(parts[:box_count])
    except Exception as e:
        print(f"[Zero Gen Error] {e}")
        return " || ".join(["Server Error"] * max(1, box_count))

# ============================================================
# CREATE MEME via API lokal /caption-image
# ============================================================
def create_meme(template_id, caption, method=None, language=None):
    """
    Mengirim caption ke API lokal /caption-image.
    - Jika template punya field 'box_positions', pakai posisi dari metadata.
    - Jika tidak, hitung otomatis berdasarkan box_count dan dimensi gambar.
    
    Args:
        template_id: ID template meme
        caption: Caption teks
        method: "zero" atau "few" (untuk naming file gambar)
        language: "id" atau "en" (untuk naming file gambar)
    
    Returns:
        Tuple (url, custom_filename) atau (url, None) jika tidak ada custom naming
    """
    template = get_meme_template(template_id)
    if not template:
        return "[Error] Template tidak ditemukan di API lokal", None

    box_count = int(template.get("box_count", 2))
    width = int(template.get("width", 600))
    height = int(template.get("height", 400))
    caption = str(caption).strip()

    # Buat custom filename jika method dan language tersedia
    custom_filename = None
    if method and language:
        custom_filename = f"{template_id}_{method}_{language}.png"

    # Cek apakah template punya metadata box_positions
    box_positions = template.get("box_positions")
    
    if box_positions:
        # Pakai posisi dari metadata (tidak hardcode)
        boxes = []
        caption_parts = caption.split("||")
        
        for i, pos in enumerate(box_positions):
            if i < len(caption_parts):
                text = caption_parts[i].strip()
            else:
                # Kalau caption kurang, gabung semua
                text = " ".join(caption_parts).strip()
            
            boxes.append({
                "text": text,
                "x": int(pos.get("x", 10)),
                "y": int(pos.get("y", 10)),
                "width": int(pos.get("width", width)),
                "height": int(pos.get("height", height))
            })
        
        # Kalau caption lebih banyak dari box_positions, gabung ke box terakhir
        if len(caption_parts) > len(box_positions):
            remaining = " ".join(caption_parts[len(box_positions):]).strip()
            if boxes:
                boxes[-1]["text"] = f"{boxes[-1]['text']} {remaining}".strip()
    else:
        # Fallback: hitung otomatis berdasarkan box_count
        if box_count <= 1:
            text = caption.replace("||", " ").strip()
            boxes = [{
                "text": text,
                "x": 10,
                "y": 10,
                "width": width,
                "height": height
            }]
        else:
            # Minimal butuh format "teksA || teksB"
            if "||" not in caption:
                return "[Error] Format caption rusak (butuh '||' untuk 2 box)", None
            a, b = caption.split("||", 1)
            boxes = [
                {
                    "text": a.strip(),
                    "x": 10,
                    "y": 10,
                    "width": width,
                    "height": height // 2
                },
                {
                    "text": b.strip(),
                    "x": 10,
                    "y": height - (height // 3),
                    "width": width,
                    "height": height // 3
                },
            ]

    # Baca max_font_size dari template jika ada
    max_font_size = template.get("max_font_size")
    
    payload = {
        "template_id": str(template_id),
        "boxes": boxes,
    }
    
    # Tambahkan max_font_size ke payload jika ada di template
    if max_font_size is not None:
        payload["max_font_size"] = int(max_font_size)
    
    # Tambahkan custom filename ke payload jika tersedia
    if custom_filename:
        payload["filename"] = custom_filename

    try:
        r = session.post(MEME_API_CAPTION, json=payload, timeout=HTTP_TIMEOUT)
        try:
            data = r.json()
        except Exception:
            return f"[Meme API Error] HTTP {r.status_code}: {r.text[:500]}", None

        if data.get("success"):
            # URL yang dikembalikan API lokal (mis: /generated_memes/xxx.png)
            url = data["data"]["url"]
            return url, custom_filename
        return f"[Meme API Error] HTTP {r.status_code}: {data.get('error', 'unknown error')}", None
    except Exception as e:
        return f"[Post Error] {e}", None

# ============================================================
# PIPELINE 1 MEME (ZERO-SHOT ONLY)
# ============================================================
def meme_pipeline_1(template_id, topic_key=None, language=None, model_name=None, temperature=None):
    """
    Generate 1 meme menggunakan zero-shot approach.
    
    Args:
        template_id: ID template meme
        topic_key: Key subtopic (optional). Pilihan: "thesis", "lecturer", "assignment"
        language: Bahasa untuk prompt (optional). Pilihan: "id", "en". Default dari DEFAULT_LANGUAGE.
        model_name: Override model tag, contoh: "qwen3.5:latest"
        temperature: Override temperature, contoh: 0.7
    
    Returns:
        {
            "captions": [caption],
            "urls": [url],
            "clip_scores": [score]
        }
    """
    global MODEL_LLM, MODEL_VLM, LLM_TEMPERATURE
    if model_name is not None:
        MODEL_LLM = model_name
        MODEL_VLM = model_name
    if temperature is not None:
        LLM_TEMPERATURE = temperature
    if language is None:
        language = DEFAULT_LANGUAGE
    start_time = time.time()

    template = get_meme_template(template_id)
    if not template:
        print("[ERROR] Template tidak ditemukan.")
        return {"captions": [], "urls": [], "clip_scores": []}

    print(f"[TEMPLATE] {template['name']}")

    # --- Describe Image once ---
    # API lokal mengirim field 'url_cleanmeme' (bukan 'url' Imgflip)
    image_path = template.get("url_cleanmeme") or template.get("url", "")
    desc = describe_image_with_ollama(image_path, language=language)
    print(f"[DESKRIPSI ({MODEL_VLM})]\n{desc[:150]}...\n") # Print sebagian aja
    # Print full VLM result
    print(f"[VLM RESULT]\n{desc}\n")

    topic = str(topic_key).strip() if topic_key else "general"
    box_count = int(template.get("box_count", 2))

    print(f"=== TOPIC: {topic} (box_count={box_count}) ===")

    cap_zero = generate_zeroshot_caption(desc, topic, box_count, language=language)

    # cap_zero = "nyoba api llalLllLALA hehe ini masi nyoba huehuehueh"
    meme_url, _ = create_meme(template_id, cap_zero, method="zero", language=language)

    # Calculate CLIP score (hanya jika meme_url valid)
    clip_score = None
    incongruity_score = None
    if meme_url and not meme_url.startswith("[Error"):
        clip_score = calculate_clip_score(meme_url, cap_zero)
        incongruity_score = calculate_crossmodal_incongruity(clip_score)

    
    # print(f"[ZERO ({MODEL_LLM})] {cap_zero} -> {meme_url}")
    print(f"[ZERO] {cap_zero} -> {meme_url}")
    if clip_score is not None:
        print(f"[CLIP SCORE] {clip_score}")
    if incongruity_score is not None:
        print(f"[CROSSMODAL INCONGRUITY] {incongruity_score}")

    run_time_seconds = round(time.time() - start_time, 3)
    print(f"[RUNTIME] {run_time_seconds}s")

    # Save to CSV
    
    save_result_to_csv(
        template_id, "zero", language, topic, cap_zero, meme_url,
        clip_score, incongruity_score, MODEL_LLM, LLM_TEMPERATURE, run_time_seconds
    )

    return {
        "captions": [cap_zero], 
        "urls": [meme_url],
        "clip_scores": [clip_score],
        "incongruity_scores": [incongruity_score],
        "run_time_seconds": run_time_seconds
    }

# ============================================================
# PIPELINE FEW-SHOT (SINGLE MEME)
# ============================================================
def meme_pipeline_few(template_id, topic_key=None, language=None, model_name=None, temperature=None):
    """
    Generate 1 meme using few-shot approach (examples from prompts.py).
    Returns same structure as meme_pipeline_1.

    Args:
        template_id: ID template meme
        topic_key: Key subtopic (optional). Pilihan: "thesis", "lecturer", "assignment"
        language: Bahasa untuk prompt (optional). Pilihan: "id", "en". Default dari DEFAULT_LANGUAGE.
        model_name: Override model tag, contoh: "qwen3.5:latest"
        temperature: Override temperature, contoh: 0.7
    """
    global MODEL_LLM, MODEL_VLM, LLM_TEMPERATURE
    if model_name is not None:
        MODEL_LLM = model_name
        MODEL_VLM = model_name
    if temperature is not None:
        LLM_TEMPERATURE = temperature
    if language is None:
        language = DEFAULT_LANGUAGE
    start_time = time.time()

    template = get_meme_template(template_id)
    if not template:
        print("[ERROR] Template tidak ditemukan.")
        return {"captions": [], "urls": [], "clip_scores": [], "incongruity_scores": []}

    print(f"[TEMPLATE] {template['name']}")

    image_path = template.get("url_cleanmeme") or template.get("url", "")
    desc = describe_image_with_ollama(image_path, language=language)
    print(f"[DESKRIPSI ({MODEL_VLM})]\n{desc[:150]}...\n")
    # Print full VLM result
    print(f"[VLM RESULT]\n{desc}\n")

    topic = str(topic_key).strip() if topic_key else "thesis"
    box_count = int(template.get("box_count", 2))

    print(f"=== TOPIC: {topic} (box_count={box_count}) ===")
    cap_few = generate_final_caption(desc, topic, box_count, topic_key=topic_key, language=language)
    meme_url, _ = create_meme(template_id, cap_few, method="few", language=language)

    clip_score = None
    incongruity_score = None
    if meme_url and not meme_url.startswith("[Error"):
        clip_score = calculate_clip_score(meme_url, cap_few)
        incongruity_score = calculate_crossmodal_incongruity(clip_score)

    print(f"[FEW] {cap_few} -> {meme_url}")
    if clip_score is not None:
        print(f"[CLIP SCORE] {clip_score}")
    if incongruity_score is not None:
        print(f"[CROSSMODAL INCONGRUITY] {incongruity_score}")

    run_time_seconds = round(time.time() - start_time, 3)
    print(f"[RUNTIME] {run_time_seconds}s")

    save_result_to_csv(
        template_id, "few", language, topic, cap_few, meme_url,
        clip_score, incongruity_score, MODEL_LLM, LLM_TEMPERATURE, run_time_seconds
    )

    return {
        "captions": [cap_few],
        "urls": [meme_url],
        "clip_scores": [clip_score],
        "incongruity_scores": [incongruity_score],
        "run_time_seconds": run_time_seconds
    }

# # ============================================================
# # PIPELINE 6 MEME (SYNCED)
# # ============================================================
# def meme_pipeline_6(template_id, language=None):
#     """
#     Generate 6 meme (zero-shot + few-shot untuk 3 subtopics).
    
#     Args:
#         template_id: ID template meme
#         language: Bahasa untuk prompt (optional). Pilihan: "id", "en". Default dari DEFAULT_LANGUAGE.
    
#     Returns:
#         {
#             "captions": [6 captions],
#             "urls": [6 urls],
#             "clip_scores": [6 scores]
#         }
#     """
#     if language is None:
#         language = DEFAULT_LANGUAGE
    
#     template = get_meme_template(template_id)
#     if not template:
#         print("[ERROR] Template tidak ditemukan.")
#         return {"captions": [], "urls": [], "clip_scores": []}

#     print(f"[TEMPLATE] {template['name']}")

#     # --- Describe Image once ---
#     # API lokal mengirim field 'url_cleanmeme' (bukan 'url' Imgflip)
#     image_path = template.get("url_cleanmeme") or template.get("url", "")
#     desc = describe_image_with_ollama(image_path, language=language)
#     print(f"[DESKRIPSI ({MODEL_VLM})]\n{desc[:150]}...\n") # Print sebagian aja

#     captions = []
#     urls = []
#     clip_scores = []
#     box_count = int(template.get("box_count", 2))
#     subtopic_keys = list(SUBTOPICS.keys())

#     # Loop 3 subtopik -> menghasilkan 6 meme
#     for idx, key in enumerate(subtopic_keys):
#         topic = SUBTOPICS[key]["topic"]
#         focus = SUBTOPICS[key]["focus"]

#         print(f"=== SUBTOPIC {idx+1}: {topic} (box_count={box_count}) ===")

#         # ---------------------------------------------------------
#         # 1) ZERO-SHOT MEME
#         # ---------------------------------------------------------
#         cap_zero = generate_zeroshot_caption(desc, topic, focus, box_count, language=language)
#         meme_url_zero, _ = create_meme(template_id, cap_zero, method="zero", language=language)
#         clip_zero = None
#         incongruity_zero = None
#         if meme_url_zero and not meme_url_zero.startswith("[Error"):
#             clip_zero = calculate_clip_score(meme_url_zero, cap_zero)
#             incongruity_zero = calculate_crossmodal_incongruity(clip_zero)

#         print(f"[ZERO ({MODEL_LLM})] {cap_zero} -> {meme_url_zero}")
#         if clip_zero is not None:
#             print(f"[CLIP SCORE] {clip_zero}")
#         if incongruity_zero is not None:
#             print(f"[CROSSMODAL INCONGRUITY] {incongruity_zero}")
#         captions.append(cap_zero)
#         urls.append(meme_url_zero)
#         clip_scores.append(clip_zero)
        
#         # Save to CSV
#         save_result_to_csv(template_id, "zero", language, topic, cap_zero, meme_url_zero, clip_zero, incongruity_zero)

#         # ---------------------------------------------------------
#         # 2) FEW-SHOT MEME (contoh dari prompts.py)
#         # ---------------------------------------------------------
#         cap_few = generate_final_caption(desc, topic, focus, box_count, topic_key=key, language=language)
#         meme_url_few, _ = create_meme(template_id, cap_few, method="few", language=language)
#         clip_few = None
#         incongruity_few = None
#         if meme_url_few and not meme_url_few.startswith("[Error"):
#             clip_few = calculate_clip_score(meme_url_few, cap_few)
#             incongruity_few = calculate_crossmodal_incongruity(clip_few)

#         print(f"[FEW ({MODEL_LLM})]  {cap_few} -> {meme_url_few}")
#         if clip_few is not None:
#             print(f"[CLIP SCORE] {clip_few}")
#         if incongruity_few is not None:
#             print(f"[CROSSMODAL INCONGRUITY] {incongruity_few}")
#         captions.append(cap_few)
#         urls.append(meme_url_few)
#         clip_scores.append(clip_few)
        
#         # Save to CSV
#         save_result_to_csv(template_id, "few", language, topic, cap_few, meme_url_few, clip_few, incongruity_few)

#         print()

#     return {
#         "captions": captions, 
#         "urls": urls,
#         "clip_scores": clip_scores,
#         "incongruity_scores": [incongruity_score]
#     }

# ============================================================
# DISPLAY ALL PROMPTS
# ============================================================
def display_all_prompts():
    """
    Menampilkan semua prompt yang digunakan dalam pipeline:
    - VLM Prompt (Image Description)
    - Zero-Shot Prompts (single & multi-box)
    - Few-Shot Prompts (single & multi-box)
    - Few-Shot Examples untuk setiap subtopic
    """
    print("\n" + "="*80)
    print("SEMUA PROMPT YANG DIGUNAKAN")
    print("="*80 + "\n")
    
    # ==================== VLM PROMPT ====================
    print("\n" + "="*80)
    print("1. VLM PROMPT (Image Description)")
    print("="*80)
    for lang in ["id", "en"]:
        lang_name = "INDONESIA" if lang == "id" else "ENGLISH"
        print(f"\n[BAHASA: {lang_name}]")
        print("-" * 80)
        prompt = DESCRIBE_IMAGE_PROMPT.get(lang, "")
        print(prompt)
        print()
    
    # ==================== ZERO-SHOT PROMPTS ====================
    print("\n" + "="*80)
    print("2. ZERO-SHOT CAPTION PROMPTS")
    print("="*80)
    for lang in ["id", "en"]:
        lang_name = "INDONESIA" if lang == "id" else "ENGLISH"
        print(f"\n[BAHASA: {lang_name}]")
        
        # Single Box
        print(f"\n{'─'*80}")
        print("SINGLE BOX:")
        print(f"{'─'*80}")
        prompt = GENERATE_ZEROSHOT_CAPTION_PROMPT.get(lang, {}).get("single_box", "")
        # Show template dengan contoh values
        example_prompt = prompt.format(
            topic="Thesis Life",
            focus="revisi tanpa akhir, dosen pembimbing sulit ditemui",
            description="mahasiswa sedang mengerjakan skripsi dengan ekspresi lelah"
        )
        print(example_prompt)
        
        # Multi Box
        print(f"\n{'─'*80}")
        print("MULTI BOX (2 text boxes):")
        print(f"{'─'*80}")
        prompt = GENERATE_ZEROSHOT_CAPTION_PROMPT.get(lang, {}).get("multi_box", "")
        example_prompt = prompt.format(
            box_count=2,
            topic="Thesis Life",
            focus="revisi tanpa akhir, dosen pembimbing sulit ditemui",
            description="mahasiswa sedang mengerjakan skripsi dengan ekspresi lelah"
        )
        print(example_prompt)
        print()
    
    # ==================== FEW-SHOT PROMPTS ====================
    print("\n" + "="*80)
    print("3. FEW-SHOT CAPTION PROMPTS")
    print("="*80)
    for lang in ["id", "en"]:
        lang_name = "INDONESIA" if lang == "id" else "ENGLISH"
        print(f"\n[BAHASA: {lang_name}]")
        
        # Single Box
        print(f"\n{'─'*80}")
        print("SINGLE BOX:")
        print(f"{'─'*80}")
        prompt = GENERATE_FINAL_CAPTION_PROMPT.get(lang, {}).get("single_box", "")
        example_prompt = prompt.format(
            description="mahasiswa sedang mengerjakan skripsi",
            topic="Thesis Life",
            focus="revisi tanpa akhir",
            fewshot_block="skripsi jalan || mental tertinggal\nbimbingan jalan || mental tertinggal"
        )
        print(example_prompt)
        
        # Multi Box
        print(f"\n{'─'*80}")
        print("MULTI BOX (2 text boxes):")
        print(f"{'─'*80}")
        prompt = GENERATE_FINAL_CAPTION_PROMPT.get(lang, {}).get("multi_box", "")
        example_prompt = prompt.format(
            description="mahasiswa sedang mengerjakan skripsi",
            topic="Thesis Life",
            focus="revisi tanpa akhir",
            box_count=2,
            fewshot_block="skripsi jalan || mental tertinggal\nbimbingan jalan || mental tertinggal"
        )
        print(example_prompt)
        print()
    
    # ==================== FEW-SHOT EXAMPLES ====================
    print("\n" + "="*80)
    print("4. FEW-SHOT EXAMPLES PER SUBTOPIC")
    print("="*80)
    
    for subtopic_key, subtopic_data in FEWSHOT_CAPTIONS.items():
        print(f"\n[SUBTOPIC: {subtopic_key.upper()}]")
        print("="*80)
        
        for lang in ["id", "en"]:
            lang_name = "INDONESIA" if lang == "id" else "ENGLISH"
            print(f"\n  [BAHASA: {lang_name}]")
            print(f"  {'-'*76}")
            
            examples = subtopic_data.get(lang, [])
            if examples:
                for idx, example in enumerate(examples, 1):
                    description = example.get("description", "")
                    caption = example.get("caption", "")
                    print(f"    Contoh {idx}:")
                    print(f"      Description: {description}")
                    print(f"      Caption:     {caption}")
                    print()
            else:
                print(f"    Tidak ada contoh untuk {lang_name}\n")
    
    print("\n" + "="*80)
    print("SELESAI - SEMUA PROMPT TELAH DITAMPILKAN")
    print("="*80 + "\n")

# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    # Pastikan server Flask (routes.meme) sudah jalan di http://127.0.0.1:5000
    # Semua hasil disimpan otomatis ke meme_generation_results.csv

    import itertools

    # ========== KONFIGURASI RUN ==========
    MODEL_NAME  = "qwen3.5:latest"
    TEMPLATES   = [f"{i:05d}" for i in range(1, 52)]          # 00001 - 00050
    TOPICS      = ["thesis", "lecturer", "assignment"]          # 3 topik
    LANGUAGES   = ["id", "en"]                                  # 2 bahasa
    TEMPERATURES = [0.3, 0.7]                                   # 2 suhu
    # Total: 50 x 2 metode x 3 topik x 2 bahasa x 2 suhu = 1200 konfigurasi

    for template_id, topic, language, temperature in itertools.product(
        TEMPLATES, TOPICS, LANGUAGES, TEMPERATURES
    ):
        # Zero-shot
        result = meme_pipeline_1(
            template_id,
            topic_key=topic,
            language=language,
            model_name=MODEL_NAME,
            temperature=temperature,
        )
        # Few-shot
        result = meme_pipeline_few(
            template_id,
            topic_key=topic,
            language=language,
            model_name=MODEL_NAME,
            temperature=temperature,
        )
