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
# Llama belum bisa melihat gambar secara native (kecuali versi vision), 
# jadi kita gunakan LLaVA untuk deskripsi gambar.
MODEL_VLM       = "qwen3-vl"
# Gunakan Qwen3-VL untuk generate text caption
MODEL_LLM       = "qwen3-vl"
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# Endpoint API lokal
MEME_API_GET    = f"{MEME_API_BASE}/get_memes"
MEME_API_CAPTION= f"{MEME_API_BASE}/caption-image"
HTTP_TIMEOUT    = 20

# ====== CSV LOGGING ======
RESULTS_CSV_PATH = os.path.join(BASE_DIR, "meme_generation_results_qwen3_vl.csv")
CSV_COLUMNS = ["run_id", "timestamp", "template_id", "method", "language", "model", "temperature", "topic", "caption", "meme_url", "clip_score", "crossmodal_incongruity"]

def initialize_csv():
    """Inisialisasi CSV jika belum ada"""
    if not os.path.exists(RESULTS_CSV_PATH):
        with open(RESULTS_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
        print(f"[CSV] Created: {RESULTS_CSV_PATH}")

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

def save_result_to_csv(template_id, method, language, topic, caption, meme_url, clip_score, incongruity_score, model, temperature):
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
                "crossmodal_incongruity": incongruity_score if incongruity_score is not None else ""
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


# ======== SUBTOPICS ========
SUBTOPICS = {
    "thesis": {
        "topic": "Thesis Life",
        "focus": "revisi tanpa akhir, dosen pembimbing sulit ditemui, burnout, data error"
    },
    "lecturer": {
        "topic": "Lecturer / Pembelajaran",
        "focus": "dosen killer, kelas membosankan, kuis mendadak, materi sulit"
    },
    "assignment": {
        "topic": "Assignment",
        "focus": "tugas menumpuk, begadang, submit terlambat, kerja kelompok toxic"
    }
}

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
        return f"[VLM Error] {e} (Pastikan model '{MODEL_VLM}' sudah di-pull)"

# ============================================================
# FEW-SHOT FINAL CAPTION (LLM: LLAMA) — pakai contoh dari prompts.py
# ============================================================
def generate_final_caption(description, topic, focus, box_count=2, topic_key=None, language=None):
    """
    Generate caption final dengan few-shot dari prompts.py.
    - box_count == 1  -> satu caption (tanpa '||')
    - box_count >= 2  -> N caption dalam satu baris: cap1 || cap2 || ... || capN
    """
    if language is None:
        language = DEFAULT_LANGUAGE
    
    fewshots_raw = (FEWSHOT_CAPTIONS.get(topic_key or "thesis") or FEWSHOT_CAPTIONS["thesis"]).get(language, [])
    # Ambil hanya teks caption dari struktur dict
    base_captions = [item.get("caption", "") for item in fewshots_raw]

    if box_count == 1:
        # Contoh satu caption: gabung "A || B" -> "A B"
        fewshot_block = "\n".join(
            c.replace(" || ", " ").strip() for c in base_captions if c.strip()
        )
        prompt_template = GENERATE_FINAL_CAPTION_PROMPT.get(language, GENERATE_FINAL_CAPTION_PROMPT["id"])
        prompt = prompt_template["single_box"].format(
            description=description,
            topic=topic,
            focus=focus,
            fewshot_block=fewshot_block
        )
    else:
        # Contoh multi-box
        fewshot_block = "\n".join(c for c in base_captions if c.strip())
        prompt_template = GENERATE_FINAL_CAPTION_PROMPT.get(language, GENERATE_FINAL_CAPTION_PROMPT["id"])
        prompt = prompt_template["multi_box"].format(
            description=description,
            topic=topic,
            focus=focus,
            box_count=box_count,
            fewshot_block=fewshot_block
        )

    try:
        resp = client.chat(
            model=MODEL_LLM,
            messages=[{'role': 'user', 'content': prompt}]
        )
        txt = resp['message']['content'].replace("\n", " ").strip()
        txt = txt.replace('"', '').replace("'", "").strip()

        if box_count == 1:
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
def generate_zeroshot_caption(description, topic, focus, box_count=2, language=None):
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
            focus=focus,
            description=description
        )
    else:
        prompt = prompt_template["multi_box"].format(
            box_count=box_count,
            topic=topic,
            focus=focus,
            description=description
        )

    try:
        resp = client.chat(
            model=MODEL_LLM,
            messages=[{'role': 'user', 'content': prompt}]
        )
        txt = resp['message']['content'].replace("\n", " ").strip()
        txt = txt.replace('"', '').replace("'", "").strip()

        if box_count == 1:
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
def meme_pipeline_1(template_id, topic_key=None, language=None):
    """
    Generate 1 meme menggunakan zero-shot approach.
    
    Args:
        template_id: ID template meme
        topic_key: Key subtopic (optional). Jika None, akan pakai subtopic pertama.
                   Pilihan: "thesis", "lecturer", "assignment"
        language: Bahasa untuk prompt (optional). Pilihan: "id", "en". Default dari DEFAULT_LANGUAGE.
    
    Returns:
        {
            "captions": [caption],
            "urls": [url],
            "clip_scores": [score]
        }
    """
    if language is None:
        language = DEFAULT_LANGUAGE

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

    # Pilih subtopic
    if topic_key is None:
        # Default: pakai subtopic pertama
        topic_key = list(SUBTOPICS.keys())[0]
    
    if topic_key not in SUBTOPICS:
        print(f"[WARNING] Topic key '{topic_key}' tidak ditemukan. Pakai default.")
        topic_key = list(SUBTOPICS.keys())[0]
    
    topic = SUBTOPICS[topic_key]["topic"]
    focus = SUBTOPICS[topic_key]["focus"]
    box_count = int(template.get("box_count", 2))

    # Jika bahasa Indonesia dan topic_key adalah 'thesis', ganti kata 'Thesis' -> 'Skripsi'
    topic_display = topic
    if topic_key == "thesis" and language == "id":
        topic_display = topic.replace("Thesis", "Skripsi")

    print(f"=== SUBTOPIC: {topic_display} (box_count={box_count}) ===")
    # Generate zero-shot caption (pakai topic_display)
    cap_zero = generate_zeroshot_caption(desc, topic_display, focus, box_count, language=language)
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

    # Save to CSV
    
    save_result_to_csv(
        template_id, "zero", language, topic_display, cap_zero, meme_url,
        clip_score, incongruity_score, MODEL_LLM, LLM_TEMPERATURE
    )

    return {
        "captions": [cap_zero], 
        "urls": [meme_url],
        "clip_scores": [clip_score],
        "incongruity_scores": [incongruity_score]

    }

# ============================================================
# PIPELINE FEW-SHOT (SINGLE MEME)
# ============================================================
def meme_pipeline_few(template_id, topic_key=None, language=None):
    """
    Generate 1 meme using few-shot approach (examples from prompts.py).
    Returns same structure as meme_pipeline_1.
    """
    if language is None:
        language = DEFAULT_LANGUAGE

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

    if topic_key is None:
        topic_key = list(SUBTOPICS.keys())[0]
    if topic_key not in SUBTOPICS:
        print(f"[WARNING] Topic key '{topic_key}' tidak ditemukan. Pakai default.")
        topic_key = list(SUBTOPICS.keys())[0]

    topic = SUBTOPICS[topic_key]["topic"]
    focus = SUBTOPICS[topic_key]["focus"]
    box_count = int(template.get("box_count", 2))

    # Jika bahasa Indonesia dan topic_key adalah 'thesis', ganti kata 'Thesis' -> 'Skripsi'
    topic_display = topic
    if topic_key == "thesis" and language == "id":
        topic_display = topic.replace("Thesis", "Skripsi")

    print(f"=== SUBTOPIC: {topic_display} (box_count={box_count}) ===")
    cap_few = generate_final_caption(desc, topic_display, focus, box_count, topic_key=topic_key, language=language)
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

    save_result_to_csv(
        template_id, "few", language, topic_display, cap_few, meme_url,
        clip_score, incongruity_score, MODEL_LLM, LLM_TEMPERATURE
    )

    return {
        "captions": [cap_few],
        "urls": [meme_url],
        "clip_scores": [clip_score],
        "incongruity_scores": [incongruity_score]
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
    # Pastikan di laptop lokal sudah: ollama pull qwen3-vl
    
    # ========== CONTOH PENGGUNAAN ==========
    # 1. Generate 1 meme dengan zero-shot (bahasa Indonesia, default subtopic pertama)
    # result = meme_pipeline_1("00001")
    
    # 2. Generate 1 meme dengan zero-shot (bahasa Inggris, subtopic tertentu)
    # result = meme_pipeline_1("00001", topic_key="thesis", language="en")
    
    # 3. Generate 6 meme (bahasa Indonesia) - hasil disimpan ke CSV otomatis
    # result = meme_pipeline_6("00001", language="id")
    
    # 4. Generate 6 meme (bahasa Inggris) - hasil disimpan ke CSV otomatis
    # result = meme_pipeline_6("00001", language="en")

    # ========== NOTES ==========
    # - Semua hasil generate akan disimpan ke meme_generation_results.csv
    # - Nama file gambar: {template_id}_{method}_{language}.png
    # - method: "zero" atau "few"
    # - language: "id" atau "en"
    # - CSV berisi: run_id, timestamp, template_id, method, language, topic, caption, meme_url, clip_score

    # ========== CONTOH TEMPLATE IDS ==========
    result = meme_pipeline_1("00043", topic_key="assignment", language="id")
    # result = meme_pipeline_few("00043", topic_key="assignment", language="id")
    # result = meme_pipeline_6("00001")
    # Uncomment dan gunakan sesuai kebutuhan
