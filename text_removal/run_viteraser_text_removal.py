import argparse
import random
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

VALID_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SCALE_CONFIG = {
    "tiny": {
        "swin_enc_embed_dim": 96,
        "swin_enc_depths": [2, 2, 6, 2],
        "swin_enc_num_heads": [3, 6, 12, 24],
        "swin_enc_window_size": 16,
        "swin_dec_depths": [2, 6, 2, 2, 2],
        "swin_dec_num_heads": [24, 12, 6, 3, 2],
        "swin_dec_window_size": 16,
    },
    "small": {
        "swin_enc_embed_dim": 96,
        "swin_enc_depths": [2, 2, 18, 2],
        "swin_enc_num_heads": [3, 6, 12, 24],
        "swin_enc_window_size": 16,
        "swin_dec_depths": [2, 18, 2, 2, 2],
        "swin_dec_num_heads": [24, 12, 6, 3, 2],
        "swin_dec_window_size": 8,
    },
    "base": {
        "swin_enc_embed_dim": 128,
        "swin_enc_depths": [2, 2, 18, 2],
        "swin_enc_num_heads": [4, 8, 16, 32],
        "swin_enc_window_size": 8,
        "swin_dec_depths": [2, 18, 2, 2, 2],
        "swin_dec_num_heads": [32, 16, 8, 4, 2],
        "swin_dec_window_size": 8,
    },
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Text removal pakai ViTEraser (AAAI 2024)."
    )
    parser.add_argument(
        "--input-path",
        required=True,
        help="Path image atau folder image input.",
    )
    parser.add_argument(
        "--output-dir",
        default="text_removal/output",
        help="Folder output hasil inpainting ViTEraser.",
    )
    parser.add_argument(
        "--viteraser-repo",
        required=True,
        help="Path folder repo ViTEraser (hasil git clone).",
    )
    parser.add_argument(
        "--weights",
        required=True,
        help="Path checkpoint .pth ViTEraser.",
    )
    parser.add_argument(
        "--scale",
        choices=sorted(SCALE_CONFIG.keys()),
        default="tiny",
        help="Preset arsitektur ViTEraser sesuai checkpoint.",
    )
    parser.add_argument(
        "--device",
        choices=["cuda", "cpu"],
        default="cuda",
        help="Device inference.",
    )
    parser.add_argument(
        "--python-exe",
        default=sys.executable,
        help="Python executable untuk menjalankan main.py ViTEraser.",
    )
    parser.add_argument(
        "--work-dir",
        default="text_removal/_work",
        help="Folder kerja sementara untuk format dataset ViTEraser.",
    )
    parser.add_argument(
        "--keep-work-dir",
        action="store_true",
        help="Simpan folder kerja sementara setelah run selesai.",
    )
    parser.add_argument(
        "--master-port",
        type=int,
        default=3151,
        help="Port distributed launcher.",
    )
    return parser.parse_args()


def list_images(input_path: Path):
    if input_path.is_file():
        if input_path.suffix.lower() not in VALID_EXTS:
            raise ValueError(f"Format file tidak didukung: {input_path}")
        return [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path tidak ditemukan: {input_path}")

    images = sorted(
        p for p in input_path.rglob("*") if p.is_file() and p.suffix.lower() in VALID_EXTS
    )
    if not images:
        raise ValueError(f"Tidak ada image di folder: {input_path}")
    return images


def prepare_scutens_test_like_dataset(images, work_dir: Path):
    data_root = work_dir / "data" / "TextErase" / "SCUT-EnsText" / "test"
    image_dir = data_root / "image"
    label_dir = data_root / "label"
    mask_dir = data_root / "mask"

    for folder in (image_dir, label_dir, mask_dir):
        folder.mkdir(parents=True, exist_ok=True)

    for idx, src in enumerate(images, start=1):
        stem = src.stem.replace(" ", "_")
        out_name = f"{idx:05d}_{stem}.jpg"
        image_out = image_dir / out_name
        label_out = label_dir / out_name
        mask_out = mask_dir / out_name

        with Image.open(src).convert("RGB") as im:
            im.save(image_out, quality=95)
            # Label dipakai dataloader/eval. Untuk mode inference murni kita isi salinan image.
            im.save(label_out, quality=95)
            blank_mask = Image.new("L", im.size, 0)
            blank_mask.save(mask_out, quality=95)

    return work_dir / "data" / "TextErase"


def append_list_arg(cmd, key, values):
    cmd.append(key)
    cmd.extend(str(v) for v in values)


def run_viteraser(args, data_root: Path):
    repo = Path(args.viteraser_repo).resolve()
    if not repo.is_dir():
        raise FileNotFoundError(f"Repo ViTEraser tidak ditemukan: {repo}")

    main_py = repo / "main.py"
    if not main_py.exists():
        raise FileNotFoundError(f"main.py tidak ditemukan di repo: {main_py}")

    weights = Path(args.weights).resolve()
    if not weights.exists():
        raise FileNotFoundError(f"Checkpoint tidak ditemukan: {weights}")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    scale_cfg = SCALE_CONFIG[args.scale]

    cmd = [
        str(Path(args.python_exe).resolve()),
        "-m",
        "torch.distributed.launch",
        "--master_port",
        str(args.master_port),
        "--nproc_per_node",
        "1",
        "--use_env",
        "main.py",
        "--eval",
        "--data_root",
        str(data_root.resolve()),
        "--val_dataset",
        "scutens_test",
        "--batch_size",
        "1",
        "--encoder",
        "swinv2",
        "--decoder",
        "swinv2",
        "--pred_mask",
        "false",
        "--intermediate_erase",
        "false",
        "--device",
        args.device,
        "--swin_enc_embed_dim",
        str(scale_cfg["swin_enc_embed_dim"]),
        "--swin_enc_window_size",
        str(scale_cfg["swin_enc_window_size"]),
        "--swin_dec_window_size",
        str(scale_cfg["swin_dec_window_size"]),
        "--output_dir",
        str(output_dir),
        "--resume",
        str(weights),
    ]
    append_list_arg(cmd, "--swin_enc_depths", scale_cfg["swin_enc_depths"])
    append_list_arg(cmd, "--swin_enc_num_heads", scale_cfg["swin_enc_num_heads"])
    append_list_arg(cmd, "--swin_dec_depths", scale_cfg["swin_dec_depths"])
    append_list_arg(cmd, "--swin_dec_num_heads", scale_cfg["swin_dec_num_heads"])

    print("[INFO] Menjalankan ViTEraser...")
    print("[INFO] Command:", " ".join(cmd))

    try:
        subprocess.run(cmd, cwd=repo, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Proses ViTEraser gagal. Cek log error di atas.") from exc


def main():
    args = parse_args()
    input_path = Path(args.input_path).resolve()
    images = list_images(input_path)

    work_dir = Path(args.work_dir).resolve()
    run_id = random.randint(1000, 9999)
    work_dir = work_dir / f"run_{run_id}"

    if work_dir.exists():
        shutil.rmtree(work_dir)

    try:
        data_root = prepare_scutens_test_like_dataset(images, work_dir)
        run_viteraser(args, data_root)
    finally:
        if args.keep_work_dir:
            print(f"[INFO] Work dir disimpan: {work_dir}")
        else:
            shutil.rmtree(work_dir, ignore_errors=True)
            print(f"[INFO] Work dir dibersihkan: {work_dir}")

    print("[DONE] Text removal selesai.")
    print(f"[DONE] Hasil output: {Path(args.output_dir).resolve() / 'SCUT-EnsText'}")


if __name__ == "__main__":
    main()
