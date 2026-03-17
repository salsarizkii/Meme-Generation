# Text Removal (ViTEraser)

Folder ini khusus pipeline text removal pakai **ViTEraser**.

## 1) Clone repo ViTEraser

```bash
git clone https://github.com/shannanyinxiang/ViTEraser.git
```

## 2) Install dependency (di environment ViTEraser)

```bash
cd ViTEraser
pip install -r requirements.txt
```

> Catatan: ViTEraser dari paper AAAI 2024 awalnya direkomendasikan di PyTorch lama (1.8.x). Kalau environment lo beda versi, pastikan kompatibel dulu.

## 3) Download checkpoint ViTEraser

Ambil file weight `.pth` sesuai skala model (`tiny`/`small`/`base`) dari README repo ViTEraser, lalu simpan lokal.

## 4) Jalankan script wrapper dari project ini

Contoh untuk input folder:

```bash
python text_removal/run_viteraser_text_removal.py \
  --input-path cleanmeme \
  --output-dir text_removal/output \
  --viteraser-repo D:/tools/ViTEraser \
  --weights D:/models/viteraser_tiny.pth \
  --scale tiny \
  --device cuda
```

Contoh untuk 1 gambar:

```bash
python text_removal/run_viteraser_text_removal.py \
  --input-path cleanmeme/patrick-nunjuk.png \
  --output-dir text_removal/output_single \
  --viteraser-repo D:/tools/ViTEraser \
  --weights D:/models/viteraser_tiny.pth \
  --scale tiny \
  --device cuda
```

## Output

Hasil akan ada di:

- `text_removal/output/SCUT-EnsText/`

Struktur output ini ngikutin cara save bawaan ViTEraser.
