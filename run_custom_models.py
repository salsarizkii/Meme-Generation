import argparse
import sys

import gemma3
import llama4
import qwen3_5
import qwen3_vl


MODEL_SPECS = {
    "llama": {"label": "llama4", "module": llama4},
    "gemma3": {"label": "gemma3", "module": gemma3},
    "qwen3_5": {"label": "qwen3.5", "module": qwen3_5},
    "qwen3_vl": {"label": "qwen3-vl", "module": qwen3_vl},
}


def get_runner(module_ref, method):
    if method == "zero":
        return module_ref.meme_pipeline_1
    if method == "few":
        return module_ref.meme_pipeline_few
    raise ValueError(f"Method tidak dikenal: {method}")


def apply_runtime_overrides(module_ref, model_name=None, temperature=None):
    """Override model/temperature di module target saat runtime."""
    if model_name is not None:
        if hasattr(module_ref, "MODEL_LLM"):
            module_ref.MODEL_LLM = model_name
        if hasattr(module_ref, "MODEL_VLM"):
            module_ref.MODEL_VLM = model_name

    if temperature is not None and hasattr(module_ref, "LLM_TEMPERATURE"):
        module_ref.LLM_TEMPERATURE = temperature


def parse_template_ids(raw_ids):
    """Parse string ID seperti '9,12,13' atau '8-10,19' jadi format 5 digit."""
    if not raw_ids:
        return []

    parsed = []
    seen = set()

    for token in raw_ids.split(","):
        token = token.strip()
        if not token:
            continue

        if "-" in token:
            start_str, end_str = token.split("-", 1)
            start = int(start_str.strip())
            end = int(end_str.strip())
            if start <= 0 or end <= 0:
                raise ValueError(f"ID harus > 0: '{token}'")
            if end < start:
                raise ValueError(f"Range tidak valid: '{token}'")
            for value in range(start, end + 1):
                if value not in seen:
                    seen.add(value)
                    parsed.append(f"{value:05d}")
        else:
            value = int(token)
            if value <= 0:
                raise ValueError(f"ID harus > 0: '{token}'")
            if value not in seen:
                seen.add(value)
                parsed.append(f"{value:05d}")

    return parsed


def run_custom_templates(
    selections,
    topic_key="lecturer",
    language="id",
    method="zero",
    model_name=None,
    temperature=None,
    dry_run=False,
):
    """
    selections: dict, contoh:
        {
            "llama": ["00009", "00012", "00013"],
            "gemma3": ["00008", "00009", "00019"],
        }
    """
    all_results = {}

    for model_key, template_ids in selections.items():
        spec = MODEL_SPECS[model_key]
        canonical_name = spec["label"]
        module_ref = spec["module"]
        runner = get_runner(module_ref, method)

        # Apply override per module yang akan di-run.
        apply_runtime_overrides(module_ref, model_name=model_name, temperature=temperature)

        active_model = getattr(module_ref, "MODEL_LLM", "-")
        active_temp = getattr(module_ref, "LLM_TEMPERATURE", "-")

        print(f"\n{'=' * 70}")
        print(f"RUN MODEL: {canonical_name}")
        print(
            f"TOPIC: {topic_key} | LANGUAGE: {language} | "
            f"METHOD: {method} | MODEL_TAG: {active_model} | TEMP: {active_temp}"
        )
        print(f"TEMPLATES: {', '.join(template_ids)}")
        print(f"{'=' * 70}")

        model_results = {}
        for template_id in template_ids:
            print(
                f"\n[RUN] model={canonical_name} | template={template_id} | "
                f"topic={topic_key} | method={method} | language={language}"
            )

            if dry_run:
                model_results[template_id] = {"dry_run": True}
                continue

            try:
                result = runner(template_id, topic_key=topic_key, language=language)
                model_results[template_id] = result
            except Exception as exc:
                print(f"[ERROR] model={canonical_name} | template={template_id} -> {exc}")
                model_results[template_id] = {"error": str(exc)}

        all_results[canonical_name] = model_results

    return all_results


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Runner custom meme pipeline per model dan per template ID. "
            "Contoh: --llama 9,12,13 --gemma3 8,9,19 --method zero"
        )
    )

    parser.add_argument("--llama", help="ID template untuk llama4. Contoh: 9,12,13")
    parser.add_argument("--gemma3", help="ID template untuk gemma3. Contoh: 8,9,19")
    parser.add_argument("--qwen3_5", help="ID template untuk qwen3.5. Contoh: 1-5,9")
    parser.add_argument("--qwen3_vl", help="ID template untuk qwen3-vl. Contoh: 3,7,11")

    parser.add_argument("--method", choices=["zero", "few"], default="zero", help="method caption (default: zero)")
    parser.add_argument("--topic", default="lecturer", help="topic_key (default: lecturer)")
    parser.add_argument("--language", default="id", help="bahasa output (default: id)")
    parser.add_argument("--model", help="override model tag, contoh: llama4:latest")
    parser.add_argument("--temperature", type=float, help="override temperature, contoh: 0.7")
    parser.add_argument("--dry-run", action="store_true", help="cuma print rencana run, tanpa eksekusi")

    return parser.parse_args()


def run_manual_main_style():
    """
    Mode manual di main, biar gaya run tetap seperti:
    result = meme_pipeline_1("00005", topic_key="lecturer", language="id")
    """
    def run_manual_one(
        template_id,
        model_key="llama",
        model_name=None,
        temperature=None,
        topic_key="lecturer",
        method="zero",
        language="id",
    ):
        spec = MODEL_SPECS[model_key]
        module_ref = spec["module"]

        apply_runtime_overrides(module_ref, model_name=model_name, temperature=temperature)
        runner = get_runner(module_ref, method)

        active_model = getattr(module_ref, "MODEL_LLM", "-")
        active_temp = getattr(module_ref, "LLM_TEMPERATURE", "-")
        print(
            "[MANUAL RUN] "
            f"model_key={model_key} | model_tag={active_model} | temp={active_temp} | "
            f"topic={topic_key} | method={method} | language={language} | template={template_id}"
        )

        return runner(template_id, topic_key=topic_key, language=language)

    # Semua konfigurasi yang dulu menghasilkan "Server Error" sudah berhasil di-run ulang.
    # Isi list ini dengan konfigurasi baru yang mau dijalankan.
    manual_runs = [
        # {
        #     "template_id": "00005",
        #     "model_key": "llama",
        #     "model_name": "llama4:latest",
        #     "temperature": 0.7,
        #     "topic_key": "lecturer",
        #     "method": "zero",
        #     "language": "id",
        # },
    ]

    result = None
    for config in manual_runs:
        result = run_manual_one(**config)

    if not manual_runs:
        print("[MANUAL MODE] Tidak ada konfigurasi aktif. Isi 'manual_runs' dulu.")

    return result


def main():
    # Kalau tanpa argumen, pakai mode manual style di atas.
    if len(sys.argv) == 1:
        run_manual_main_style()
        return 0

    args = parse_args()

    raw_selection_map = {
        "llama": args.llama,
        "gemma3": args.gemma3,
        "qwen3_5": args.qwen3_5,
        "qwen3_vl": args.qwen3_vl,
    }

    selections = {}
    for model_key, raw_ids in raw_selection_map.items():
        if raw_ids:
            try:
                selections[model_key] = parse_template_ids(raw_ids)
            except ValueError as exc:
                print(f"[INPUT ERROR] {model_key}: {exc}")
                return 1

    if not selections:
        print("[INPUT ERROR] Minimal pilih 1 model.")
        print("Contoh: python run_custom_models.py --llama 9,12,13 --gemma3 8,9,19 --method zero")
        return 1

    results = run_custom_templates(
        selections,
        topic_key=args.topic,
        language=args.language,
        method=args.method,
        model_name=args.model,
        temperature=args.temperature,
        dry_run=args.dry_run,
    )

    print(f"\n{'=' * 70}")
    print("RINGKASAN")
    print(f"{'=' * 70}")

    for model_name, model_results in results.items():
        success_count = sum(
            1
            for value in model_results.values()
            if isinstance(value, dict) and "error" not in value
        )
        error_count = len(model_results) - success_count
        print(f"- {model_name}: success={success_count}, error={error_count}")

    return 0


if __name__ == "__main__":
    # Contoh beda model + beda setting per run:
    # result = run_manual_one("00008", model_key="gemma3", model_name="gemma3:27b", temperature=0.7, topic_key="assignment", method="few", language="id")
    # result = run_manual_one("00019", model_key="qwen3_5", model_name="qwen3.5:latest", temperature=0.5, topic_key="thesis", method="zero", language="en")
    raise SystemExit(main())
