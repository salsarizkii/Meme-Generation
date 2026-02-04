from flask import Blueprint, request, jsonify
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import json
import os
import time
import requests
import textwrap

caption_bp = Blueprint("caption", __name__)

# Path absolut ke project root
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MEMES_PATH = os.path.join(BASE_DIR, "memes.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "generated_memes")
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(MEMES_PATH, encoding="utf-8") as f:
    MEMES = json.load(f)


def _load_image(path_or_url: str) -> Image.Image:
    """Bisa load dari path lokal (mis: memes/xxx.jpg) atau URL penuh."""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        resp = requests.get(path_or_url, timeout=15)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGBA")
    # path relatif dari project root
    rel_path = path_or_url.lstrip("/")
    full_path = os.path.join(BASE_DIR, rel_path)
    return Image.open(full_path).convert("RGBA")


def _get_font(preferred_font: str | None, max_font_size: int | None, require_ttf: bool = True):
    size = max_font_size or 40
    # Coba font Impact / TTF, kalau gagal pakai default
    candidates = []
    if preferred_font:
        # kalau user kirim "impact", kita coba impact.ttf
        if preferred_font.lower().endswith(".ttf"):
            candidates.append(preferred_font)
        else:
            candidates.append(preferred_font + ".ttf")
    candidates.append("impact.ttf")

    for name in candidates:
        try:
            # coba cari di folder fonts/ lalu project root
            font_path = os.path.join(BASE_DIR, "fonts", name)
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size=size)
            font_path = os.path.join(BASE_DIR, name)
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size=size)
            # atau dari sistem (by name)
            return ImageFont.truetype(name, size=size)
        except Exception:
            continue

    # Fallback: cek lokasi font Windows secara eksplisit
    windows_font_candidates = [
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibrib.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
    ]
    for fp in windows_font_candidates:
        try:
            if os.path.exists(fp):
                return ImageFont.truetype(fp, size=size)
        except Exception:
            continue

    if require_ttf:
        raise RuntimeError(
            "Font TTF tidak ditemukan. Taruh 'impact.ttf' (atau font .ttf lain) di folder project "
            f"({BASE_DIR}) atau pastikan ada di C:\\Windows\\Fonts."
        )

    # Terakhir: hanya kalau require_ttf = False
    return ImageFont.load_default()


@caption_bp.route("/caption-image", methods=["POST"])
def caption_image():
    """
    Contoh payload yang didukung (mirip Imgflip, tapi ke gambar lokal):
    {
      "template_id": "61579",
      "font": "impact",
      "max_font_size": 50,
      "color": "#ffffff",
      "outline_color": "#000000",
      "boxes": [
        {
          "text": "KETIKA KODE PROGRAM LANGSUNG JALAN"
        },
        {
          "text": "PADAHAL BARU SEKALI RUNNING"
        }
      ]
    }

    Atau dengan posisi manual per box:
    {
      "template_id": "61579",
      "boxes": [
        {
          "text": "Saya sedang belajar API",
          "x": 10, "y": 10, "width": 548, "height": 100
        },
        {
          "text": "JSON-nya sangat rapi",
          "x": 10, "y": 225, "width": 548, "height": 100,
          "color": "#00ff00",
          "outline_color": "#000000"
        }
      ]
    }
    """
    data = request.get_json(force=True, silent=True) or {}

    template_id = str(data.get("template_id", "")).strip()
    if not template_id:
        return jsonify({"success": False, "error": "template_id is required"}), 400

    meme = next((m for m in MEMES if str(m["id"]) == template_id), None)
    if not meme:
        return jsonify({"success": False, "error": "Template not found"}), 404

    try:
        img = _load_image(meme["url_cleanmeme"])
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to load image: {e}"}), 500

    draw = ImageDraw.Draw(img)

    # default value dari body, fallback ke template (memes.json)
    # sehingga warna teks & outline bisa diatur per-template
    default_color = data.get("color") or meme.get("color", "#ffffff")
    default_outline = data.get("outline_color") or meme.get("outline_color", "#000000")
    default_stroke_width = meme.get("stroke_width", 2)
    max_font_size = data.get("max_font_size")
    if max_font_size is None and meme.get("max_font_size") is not None:
        max_font_size = meme["max_font_size"]
    # Default: selalu pakai TTF (tanpa perlu set di memes.json)
    # - Prioritas font: request.box/font -> request.font -> template.font -> impact
    # - Lokasi: project/fonts/*.ttf, project root, lalu C:\Windows\Fonts
    font_name = data.get("font") or meme.get("font") or "impact"

    try:
        font = _get_font(font_name, max_font_size, require_ttf=True)
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to load TTF font: {e}"}), 500

    boxes = data.get("boxes") or []
    if not boxes:
        return jsonify({"success": False, "error": "boxes is required"}), 400

    for i, box in enumerate(boxes):
        text = str(box.get("text", ""))
        if not text:
            continue

        # Ambil posisi dan dimensi box
        box_x = box.get("x")
        box_y = box.get("y")
        box_width = box.get("width")
        box_height = box.get("height")
        
        # posisi default: box 0 di atas, box 1 di bawah
        if box_x is None or box_y is None:
            box_x = 10
            if i == 0:
                box_y = 10
            else:
                box_y = img.height - (max_font_size or 50) - 10
        
        # Jika width/height tidak ada, gunakan default
        if box_width is None:
            box_width = img.width - box_x - 10
        if box_height is None:
            box_height = img.height - box_y - 10

        color = box.get("color", default_color)
        outline_color = box.get("outline_color", default_outline)
        stroke_width = box.get("stroke_width", default_stroke_width)

        # Hitung tinggi baris teks
        try:
            bbox = draw.textbbox((0, 0), "Ag", font=font)  # Test dengan karakter tinggi
            line_height = bbox[3] - bbox[1]
            text_ascent = -bbox[1]
        except AttributeError:
            bbox = draw.textbbox((0, 0), "Ag", font=font)
            line_height = bbox[3] - bbox[1]
            text_ascent = -bbox[1]

        # Wrap teks berdasarkan width box
        # Estimasi jumlah karakter per baris berdasarkan width
        # Kita coba wrap manual dengan textwrap, lalu adjust berdasarkan actual width
        words = text.split()
        if not words:
            continue
        
        # Estimasi karakter per baris (rough estimate)
        try:
            avg_char_width = draw.textlength("M", font=font)  # M adalah karakter lebar
        except AttributeError:
            bbox_m = draw.textbbox((0, 0), "M", font=font)
            avg_char_width = bbox_m[2] - bbox_m[0]
        
        # Hitung max karakter per baris
        max_chars_per_line = int(box_width / avg_char_width) if avg_char_width > 0 else 20
        
        # Wrap teks
        wrapped_lines = []
        current_line = []
        current_line_text = ""
        
        for word in words:
            test_line = (current_line_text + " " + word).strip() if current_line_text else word
            try:
                test_width = draw.textlength(test_line, font=font)
            except AttributeError:
                bbox_test = draw.textbbox((0, 0), test_line, font=font)
                test_width = bbox_test[2] - bbox_test[0]
            
            if test_width <= box_width or not current_line_text:
                # Masih muat atau ini kata pertama
                current_line.append(word)
                current_line_text = test_line
            else:
                # Tidak muat, simpan baris sebelumnya dan mulai baris baru
                wrapped_lines.append(" ".join(current_line))
                current_line = [word]
                current_line_text = word
        
        # Tambahkan baris terakhir
        if current_line:
            wrapped_lines.append(" ".join(current_line))
        
        # Hitung total tinggi teks
        total_text_height = len(wrapped_lines) * line_height
        
        # Center vertikal jika total height < box_height
        start_y = box_y
        if total_text_height < box_height:
            start_y = box_y + (box_height - total_text_height) // 2
        
        # Render setiap baris dengan center alignment horizontal
        current_y = start_y + text_ascent
        
        for line in wrapped_lines:
            if current_y + line_height > box_y + box_height:
                break  # Jangan render jika melebihi box height
            
            # Hitung lebar baris untuk center alignment
            try:
                line_width = draw.textlength(line, font=font)
            except AttributeError:
                bbox_line = draw.textbbox((0, 0), line, font=font)
                line_width = bbox_line[2] - bbox_line[0]
            
            # Center horizontal: x adalah center point, adjust untuk center alignment
            line_x = box_x - (line_width / 2)
            
            # Render baris dengan outline (fallback aman jika font tidak support stroke)
            try:
                if stroke_width and outline_color:
                    draw.text(
                        (line_x, current_y),
                        line,
                        font=font,
                        fill=color,
                        stroke_width=int(stroke_width),
                        stroke_fill=outline_color,
                    )
                else:
                    draw.text((line_x, current_y), line, font=font, fill=color)
            except Exception:
                # Fallback universal: render tanpa stroke
                draw.text((line_x, current_y), line, font=font, fill=color)
            
            current_y += line_height

    filename = f"meme_{int(time.time())}.png"
    output_path = os.path.join(OUTPUT_DIR, filename)
    img.save(output_path)

    return jsonify({
        "success": True,
        "data": {
            # URL relatif; nanti bisa di-serve via static atau nginx
            "url": f"/generated_memes/{filename}"
        }
    })

