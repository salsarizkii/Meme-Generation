from io import BytesIO
import time
import requests
import os
import ollama  # Library Ollama
from dotenv import load_dotenv
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from prompts import FEWSHOT_CAPTIONS

# ====== LOAD ENV VARS ======
load_dotenv()

# Path dasar project (lokasi file ini)
BASE_DIR = os.path.dirname(__file__)

# ====== KONFIGURASI API MEME LOKAL ======
# Contoh: Flask di routes/meme.py jalan di localhost:5000
MEME_API_BASE   = os.getenv("MEME_API_BASE", "http://127.0.0.1:5000")

# ====== KONFIGURASI OLLAMA ======
# Sesuaikan IP dengan server Anda
OLLAMA_HOST     = "http://152.42.226.64:11434"

# MODEL KONFIGURASI
# Llama belum bisa melihat gambar secara native (kecuali versi vision), 
# jadi kita gunakan LLaVA untuk deskripsi gambar.
MODEL_VLM       = "llama4"           
# Gunakan Llama untuk generate text caption
MODEL_LLM       = "llama4" # Ganti ke 'llama4' jika nanti sudah rilis

# Endpoint API lokal
MEME_API_GET    = f"{MEME_API_BASE}/get_memes"
MEME_API_CAPTION= f"{MEME_API_BASE}/caption-image"
HTTP_TIMEOUT    = 20

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
def describe_image_with_ollama(path_or_url):
    """
    Menerima:
    - URL penuh (http/https), atau
    - path lokal relatif dari root project (mis: cleanmeme/pisau-pisau.jpg atau /cleanmeme/...)
    """
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

        prompt = """Analisis gambar meme template ini secara detail:
        
1. Identifikasi karakter/objek utama:
   - Siapa atau apa yang ada di gambar?
   - Ekspresi wajah dan bahasa tubuh?
   - Posisi dalam frame?

2. Deskripsi visual:
   - Setting/latar belakang
   - Warna dominan
   - Komposisi visual
   - Area yang kosong untuk teks

3. Konteks meme:
   - Mood/emosi yang ditampilkan
   - Potensi konteks humor
   - Dinamika antara elemen visual

Berikan deskripsi objektif minimal 120 kata yang bisa membantu membuat caption meme yang relevan."""

        # 2. Kirim ke Ollama
        resp = client.chat(
            model=MODEL_VLM,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_bytes]  # Ollama menerima list bytes
            }]
        )

        return resp['message']['content']
    except Exception as e:
        return f"[VLM Error] {e} (Pastikan model '{MODEL_VLM}' sudah di-pull)"

# ============================================================
# FEW-SHOT FINAL CAPTION (LLM: LLAMA) — pakai contoh dari prompts.py
# ============================================================
def generate_final_caption(description, topic, focus, box_count=2, topic_key=None):
    """
    Generate caption final dengan few-shot dari prompts.py.
    - box_count == 1  -> satu caption (tanpa '||')
    - box_count >= 2  -> N caption dalam satu baris: cap1 || cap2 || ... || capN
    """
    fewshots_raw = FEWSHOT_CAPTIONS.get(topic_key or "thesis") or FEWSHOT_CAPTIONS["thesis"]
    # Ambil hanya teks caption dari struktur dict
    base_captions = [item.get("caption", "") for item in fewshots_raw]

    if box_count == 1:
        # Contoh satu caption: gabung "A || B" -> "A B"
        fewshot_block = "\n".join(
            c.replace(" || ", " ").strip() for c in base_captions if c.strip()
        )
        prompt = f"""
Anda adalah generator caption meme untuk mahasiswa.
Deskripsi template: {description}...

TOPIK: {topic}
FOKUS HUMOR: {focus}

CONTOH CAPTION (FEW-SHOT, SATU BARIS): 
{fewshot_block}

TUGAS: Buat SATU caption meme (satu kalimat saja, tanpa pemisah ||).
KETENTUAN: Sangat singkat (maks 10 kata), lucu/satir, relatable mahasiswa, relevan dengan deskripsi.
OUTPUT: HANYA SATU BARIS caption, tanpa penjelasan.

Caption baru Anda:"""
    else:
        # Contoh multi-box tetap 2 box, tapi cukup untuk gaya humor
        fewshot_block = "\n".join(c for c in base_captions if c.strip())
        prompt = f"""
Anda adalah generator caption meme untuk mahasiswa.
Deskripsi template: {description}...

TOPIK: {topic}
FOKUS HUMOR: {focus}

CONTOH CAPTION (FEW-SHOT, 2 BOX): 
{fewshot_block}

TUGAS: Buat SATU caption dengan {box_count} box.
Gabungkan SEMUA teks dalam SATU BARIS dengan format:
teks1 || teks2 || ... || teks{box_count}

KETENTUAN:
- Sangat singkat (1-4 kata per box)
- Lucu/satir/relatable untuk mahasiswa
- Relevan dengan deskripsi template
OUTPUT: HANYA SATU BARIS dengan format di atas, tanpa penjelasan.

Caption baru Anda:"""

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
def generate_zeroshot_caption(description, topic, focus, box_count=2):
    """
    Zero-shot caption:
    - box_count == 1  -> satu caption (tanpa '||')
    - box_count >= 2  -> N caption dalam satu baris: cap1 || cap2 || ... || capN
    """
    if box_count == 1:
        prompt = f"""
Anda adalah generator caption meme untuk mahasiswa.
Buat SATU caption meme saja (satu kalimat, tanpa pemisah ||).

Batasan: Sangat singkat (maks 10 kata), lucu/satir/relatable, relevan kehidupan mahasiswa.
Topik: {topic}
Fokus humor: {focus}

Deskripsi gambar: "{description}"

OUTPUT: HANYA SATU BARIS caption, tanpa penjelasan."""
    else:
        prompt = f"""
Anda adalah generator caption meme untuk mahasiswa.
Buat {box_count} teks meme singkat.
Gabungkan SEMUA teks dalam SATU BARIS dengan format:
teks1 || teks2 || ... || teks{box_count}

Batasan:
- Sangat singkat (1–4 kata per box)
- Lucu / satir / relatable
- Relevan dengan kehidupan mahasiswa
- OUTPUT HANYA SATU BARIS dengan pemisah '||'

Topik: {topic}
Fokus humor: {focus}

Deskripsi gambar: "{description}"
"""

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
def create_meme(template_id, caption):
    """
    Mengirim caption ke API lokal /caption-image.
    - Jika template punya field 'box_positions', pakai posisi dari metadata.
    - Jika tidak, hitung otomatis berdasarkan box_count dan dimensi gambar.
    """
    template = get_meme_template(template_id)
    if not template:
        return "[Error] Template tidak ditemukan di API lokal"

    box_count = int(template.get("box_count", 2))
    width = int(template.get("width", 600))
    height = int(template.get("height", 400))
    caption = str(caption).strip()

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
                return "[Error] Format caption rusak (butuh '||' untuk 2 box)"
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

    try:
        r = session.post(MEME_API_CAPTION, json=payload, timeout=HTTP_TIMEOUT)
        try:
            data = r.json()
        except Exception:
            return f"[Meme API Error] HTTP {r.status_code}: {r.text[:500]}"

        if data.get("success"):
            # URL yang dikembalikan API lokal (mis: /generated_memes/xxx.png)
            return data["data"]["url"]
        return f"[Meme API Error] HTTP {r.status_code}: {data.get('error', 'unknown error')}"
    except Exception as e:
        return f"[Post Error] {e}"

# ============================================================
# PIPELINE 1 MEME (ZERO-SHOT ONLY)
# ============================================================
def meme_pipeline_1(template_id, topic_key=None):
    """
    Generate 1 meme menggunakan zero-shot approach.
    
    Args:
        template_id: ID template meme
        topic_key: Key subtopic (optional). Jika None, akan pakai subtopic pertama.
                   Pilihan: "thesis", "lecturer", "assignment"
    
    Returns:
        {
            "captions": [caption],
            "urls": [url]
        }
    """

    template = get_meme_template(template_id)
    if not template:
        print("[ERROR] Template tidak ditemukan.")
        return {"captions": [], "urls": []}

    print(f"[TEMPLATE] {template['name']}")

    # --- Describe Image once ---
    # API lokal mengirim field 'url_cleanmeme' (bukan 'url' Imgflip)
    image_path = template.get("url_cleanmeme") or template.get("url", "")
    desc = describe_image_with_ollama(image_path)
    print(f"[DESKRIPSI ({MODEL_VLM})]\n{desc[:150]}...\n") # Print sebagian aja

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

    print(f"=== SUBTOPIC: {topic} (box_count={box_count}) ===")
    # Generate zero-shot caption
    cap_zero = generate_zeroshot_caption(desc, topic, focus, box_count)
    # cap_zero = "nyoba api llalLllLALA hehe ini masi nyoba huehuehueh"
    meme_zero = create_meme(template_id, cap_zero)


    # print(f"[ZERO ({MODEL_LLM})] {cap_zero} -> {meme_zero}")
    print(f"[ZERO] {cap_zero} -> {meme_zero}")

    return {
        "captions": [cap_zero], 
        "urls": [meme_zero]         
    }

# ============================================================
# PIPELINE 6 MEME (SYNCED)
# ============================================================
def meme_pipeline_6(template_id):
    template = get_meme_template(template_id)
    if not template:
        print("[ERROR] Template tidak ditemukan.")
        return {"captions": [], "urls": []}

    print(f"[TEMPLATE] {template['name']}")

    # --- Describe Image once ---
    # API lokal mengirim field 'url_cleanmeme' (bukan 'url' Imgflip)
    image_path = template.get("url_cleanmeme") or template.get("url", "")
    desc = describe_image_with_ollama(image_path)
    print(f"[DESKRIPSI ({MODEL_VLM})]\n{desc[:150]}...\n") # Print sebagian aja

    captions = []
    urls = []
    box_count = int(template.get("box_count", 2))
    subtopic_keys = list(SUBTOPICS.keys())

    # Loop 3 subtopik -> menghasilkan 6 meme
    for idx, key in enumerate(subtopic_keys):
        topic = SUBTOPICS[key]["topic"]
        focus = SUBTOPICS[key]["focus"]

        print(f"=== SUBTOPIC {idx+1}: {topic} (box_count={box_count}) ===")

        # ---------------------------------------------------------
        # 1) ZERO-SHOT MEME
        # ---------------------------------------------------------
        cap_zero = generate_zeroshot_caption(desc, topic, focus, box_count)
        meme_zero = create_meme(template_id, cap_zero)

        print(f"[ZERO ({MODEL_LLM})] {cap_zero} -> {meme_zero}")
        captions.append(cap_zero)
        urls.append(meme_zero)

        # ---------------------------------------------------------
        # 2) FEW-SHOT MEME (contoh dari prompts.py)
        # ---------------------------------------------------------
        cap_few = generate_final_caption(desc, topic, focus, box_count, topic_key=key)
        meme_few = create_meme(template_id, cap_few)

        print(f"[FEW ({MODEL_LLM})]  {cap_few} -> {meme_few}")
        captions.append(cap_few)
        urls.append(meme_few)

        print()

    return {
        "captions": captions, 
        "urls": urls         
    }

# ============================================================
# RUN
# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    # Pastikan server Flask (routes.meme) sudah jalan di http://127.0.0.1:5000
    # Pastikan di server sudah: ollama pull llava && ollama pull llama3.2
    
    # Contoh penggunaan:
    # 1. Generate 1 meme dengan zero-shot (default subtopic pertama)
    # result = meme_pipeline_1("00001")
    
    # 2. Generate 1 meme dengan zero-shot (subtopic tertentu)

    # result = meme_pipeline_1("00035", topic_key="asignment")
    # result = meme_pipeline_1("00036", topic_key="asignment")
    # result = meme_pipeline_1("00037", topic_key="asignment")
    # result = meme_pipeline_1("00038", topic_key="asignment")
    # result = meme_pipeline_1("00039", topic_key="asignment")
    # result = meme_pipeline_1("00040", topic_key="asignment")
    # result = meme_pipeline_1("00041", topic_key="asignment")
    # result = meme_pipeline_1("00042", topic_key="asignment")
    # result = meme_pipeline_1("00043", topic_key="asignment")
    result = meme_pipeline_1("00044", topic_key="asignment")
    # result = meme_pipeline_1("00045", topic_key="asignment")
    # result = meme_pipeline_1("00046", topic_key="asignment")
    # result = meme_pipeline_1("00047", topic_key="asignment")
    # result = meme_pipeline_1("00048", topic_key="asignment")
    # result = meme_pipeline_1("00049", topic_key="asignment")
    # result = meme_pipeline_1("00050", topic_key="asignment")
    # result = meme_pipeline_1("00051", topic_key="asignment")
    

    # 3. Generate 6 meme (zero-shot + few-shot untuk 3 subtopics)
    # result = meme_pipeline_6("00001")
    
    # Contoh default:
    # meme_pipeline_6("00001")