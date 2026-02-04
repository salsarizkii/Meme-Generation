#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os

# Baca memes.json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMES_PATH = os.path.join(BASE_DIR, "memes.json")

with open(MEMES_PATH, 'r', encoding='utf-8') as f:
    memes = json.load(f)

# Tambahkan max_font_size berdasarkan ukuran gambar
for meme in memes:
    if "max_font_size" not in meme:
        width = meme.get("width", 600)
        height = meme.get("height", 400)
        
        # Tentukan font size berdasarkan ukuran gambar
        # Gambar besar (>1500px): font size 60-80
        # Gambar sedang (800-1500px): font size 40-60
        # Gambar kecil (<800px): font size 30-50
        max_dimension = max(width, height)
        
        if max_dimension > 2000:
            max_font_size = 80
        elif max_dimension > 1500:
            max_font_size = 70
        elif max_dimension > 1000:
            max_font_size = 60
        elif max_dimension > 800:
            max_font_size = 50
        else:
            max_font_size = 40
        
        meme["max_font_size"] = max_font_size

# Simpan kembali
with open(MEMES_PATH, 'w', encoding='utf-8') as f:
    json.dump(memes, f, indent=2, ensure_ascii=False)

print(f"Added max_font_size to {len(memes)} templates")
