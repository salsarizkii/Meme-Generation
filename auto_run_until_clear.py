import argparse
import csv
import itertools
import json
import time
from collections import defaultdict

import run_custom_models


def get_all_template_ids(memes_path="memes.json"):
    with open(memes_path, "r", encoding="utf-8") as f:
        memes = json.load(f)

    template_ids = []
    for meme in memes:
        template_id = str(meme.get("id", "")).strip()
        if template_id:
            template_ids.append(template_id)

    if not template_ids:
        raise ValueError("Tidak ada template di memes.json")

    return template_ids


def parse_template_ids(raw_value):
    if str(raw_value).strip().lower() == "all":
        return get_all_template_ids()

    values = []
    seen = set()

    for token in raw_value.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start_s, end_s = token.split("-", 1)
            start = int(start_s.strip())
            end = int(end_s.strip())
            if end < start:
                raise ValueError(f"Range template tidak valid: {token}")
            for x in range(start, end + 1):
                tid = f"{x:05d}"
                if tid not in seen:
                    seen.add(tid)
                    values.append(tid)
        else:
            tid = f"{int(token):05d}"
            if tid not in seen:
                seen.add(tid)
                values.append(tid)

    if not values:
        raise ValueError("Template list kosong")
    return values


def parse_csv_list(raw_value):
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    if not values:
        raise ValueError("List kosong")
    return values


def parse_temperature_list(raw_value):
    values = []
    for item in parse_csv_list(raw_value):
        values.append(float(item))
    return values


def is_server_error_caption(caption):
    txt = str(caption or "").strip().lower()
    return "server error" in txt or "server eror" in txt


def normalize_temperature(value):
    if value is None or str(value).strip() == "":
        return ""
    try:
        return f"{float(value):.6f}"
    except Exception:
        return str(value).strip()


def model_tag_from_key(model_key):
    module_ref = run_custom_models.MODEL_SPECS[model_key]["module"]
    return getattr(module_ref, "MODEL_LLM", None)


def model_key_from_tag(model_tag):
    tag = str(model_tag or "").strip().lower()
    if tag.startswith("llama4"):
        return "llama"
    if tag.startswith("gemma3"):
        return "gemma3"
    if tag.startswith("qwen3.5"):
        return "qwen3_5"
    if tag.startswith("qwen3-vl") or tag.startswith("qwen3vl"):
        return "qwen3_vl"
    return None


def build_run_plan(template_ids, model_keys, temperatures, methods, topics, languages):
    plan = []
    for model_key in model_keys:
        model_name = model_tag_from_key(model_key)
        for temperature, method, topic, language in itertools.product(temperatures, methods, topics, languages):
            plan.append(
                {
                    "model_key": model_key,
                    "template_ids": template_ids,
                    "method": method,
                    "topic": topic,
                    "language": language,
                    "model_name": model_name,
                    "temperature": temperature,
                }
            )
    return plan


def run_plan(plan):
    total_calls = len(plan)
    print(f"[PLAN] Total konfigurasi: {total_calls}")
    for idx, cfg in enumerate(plan, start=1):
        print(
            f"\n[PLAN RUN {idx}/{total_calls}] model_key={cfg['model_key']} | method={cfg['method']} | "
            f"topic={cfg['topic']} | language={cfg['language']} | model={cfg['model_name']} | temp={cfg['temperature']}"
        )
        run_custom_models.run_custom_templates(
            selections={cfg["model_key"]: cfg["template_ids"]},
            topic_key=cfg["topic"],
            language=cfg["language"],
            method=cfg["method"],
            model_name=cfg["model_name"],
            temperature=cfg["temperature"],
            dry_run=False,
        )


def get_latest_rows_by_config(csv_path):
    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row["_run_id_int"] = int(row.get("run_id", "0") or 0)
            except Exception:
                row["_run_id_int"] = 0
            rows.append(row)

    rows.sort(key=lambda r: r["_run_id_int"])

    latest = {}
    for row in rows:
        key = (
            str(row.get("template_id", "")).strip(),
            str(row.get("method", "")).strip().lower(),
            str(row.get("language", "")).strip().lower(),
            str(row.get("model", "")).strip(),
            normalize_temperature(row.get("temperature", "")),
            str(row.get("topic", "")).strip(),
        )
        latest[key] = row

    return latest


def build_retry_groups(csv_path):
    latest = get_latest_rows_by_config(csv_path)
    grouped = defaultdict(list)

    for key, row in latest.items():
        template_id, method, language, model_name, temp_norm, topic = key
        if not is_server_error_caption(row.get("caption", "")):
            continue

        model_key = model_key_from_tag(model_name)
        if model_key is None:
            print(f"[WARN] Skip retry karena model tag tidak dikenali: {model_name}")
            continue

        temp_value = None if temp_norm == "" else float(temp_norm)
        group_key = (model_key, model_name, temp_value, topic, method, language)
        grouped[group_key].append(template_id)

    retry_configs = []
    for group_key, template_ids in grouped.items():
        model_key, model_name, temp_value, topic, method, language = group_key
        retry_configs.append(
            {
                "model_key": model_key,
                "template_ids": sorted(set(template_ids)),
                "method": method,
                "topic": topic,
                "language": language,
                "model_name": model_name,
                "temperature": temp_value,
            }
        )

    return retry_configs


def run_retries_until_clear(csv_path, max_retry_rounds, cooldown_seconds):
    for round_idx in range(1, max_retry_rounds + 1):
        retry_plan = build_retry_groups(csv_path)
        if not retry_plan:
            print(f"[RETRY] Clear. Tidak ada Server Error tersisa (round={round_idx - 1}).")
            return True

        print(f"\n[RETRY ROUND {round_idx}] ditemukan {len(retry_plan)} konfigurasi error terbaru")
        run_plan(retry_plan)

        if cooldown_seconds > 0:
            print(f"[RETRY] cooldown {cooldown_seconds}s")
            time.sleep(cooldown_seconds)

    final_retry_plan = build_retry_groups(csv_path)
    if final_retry_plan:
        print(f"[RETRY] Belum clear setelah {max_retry_rounds} round.")
        return False

    print(f"[RETRY] Clear setelah {max_retry_rounds} round.")
    return True


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run semua kombinasi konfigurasi lalu retry otomatis untuk hasil caption Server Error "
            "sampai clear atau sampai batas retry."
        )
    )

    parser.add_argument("--csv-path", default="meme_generation_results.csv", help="path CSV hasil run")

    parser.add_argument("--templates", default="all", help="contoh: all, 1-10, atau 1,2,5")
    parser.add_argument("--models", default="qwen3_5", help="model keys dipisah koma")
    parser.add_argument("--methods", default="zero,few", help="zero,few")
    parser.add_argument("--topics", default="thesis,lecturer,assignment", help="topic keys dipisah koma")
    parser.add_argument("--languages", default="id,en", help="bahasa dipisah koma")

    parser.add_argument(
        "--temperatures",
        default="0.3,0.7",
        help="daftar temperature dipisah koma, contoh: 0.3,0.7,1.0",
    )
    parser.add_argument("--max-retry-rounds", type=int, default=5, help="maksimal loop retry")
    parser.add_argument("--cooldown-seconds", type=float, default=0.0, help="jeda antar retry round")
    parser.add_argument("--skip-initial-run", action="store_true", help="langsung retry dari data CSV terbaru")

    return parser.parse_args()


def main():
    args = parse_args()

    template_ids = parse_template_ids(args.templates)
    model_keys = parse_csv_list(args.models)
    temperatures = parse_temperature_list(args.temperatures)
    methods = [x.lower() for x in parse_csv_list(args.methods)]
    topics = parse_csv_list(args.topics)
    languages = [x.lower() for x in parse_csv_list(args.languages)]

    invalid_models = [m for m in model_keys if m not in run_custom_models.MODEL_SPECS]
    if invalid_models:
        raise ValueError(f"Model key tidak valid: {invalid_models}")

    invalid_methods = [m for m in methods if m not in {"zero", "few"}]
    if invalid_methods:
        raise ValueError(f"Method tidak valid: {invalid_methods}")

    if not args.skip_initial_run:
        full_plan = build_run_plan(
            template_ids=template_ids,
            model_keys=model_keys,
            temperatures=temperatures,
            methods=methods,
            topics=topics,
            languages=languages,
        )
        run_plan(full_plan)

    ok = run_retries_until_clear(
        csv_path=args.csv_path,
        max_retry_rounds=args.max_retry_rounds,
        cooldown_seconds=args.cooldown_seconds,
    )

    if ok:
        print("[DONE] Semua konfigurasi sudah clear dari Server Error (berdasarkan status terbaru).")
        return 0

    print("[DONE] Masih ada Server Error setelah retry maksimal.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
