import argparse
import importlib


DEFAULT_TOPIC = "lecturer"
DEFAULT_MODE = "zero"
DEFAULT_LANGUAGE = "id"
DEFAULT_TEMPLATE_START = 9
DEFAULT_TEMPLATE_END = 9
DEFAULT_MODELS = ["qwen3_5", "llama4"]

MODEL_MODULES = {
    "llama4": "llama4",
    "qwen3_5": "qwen3_5",
    "gemma3": "gemma3",
    "devstral": "devstral",
}


def _load_runner(model_name, mode):
    module_name = MODEL_MODULES[model_name]
    module = importlib.import_module(module_name)
    runner_name = "meme_pipeline_1" if mode == "zero" else "meme_pipeline_few"
    return getattr(module, runner_name)


def run_templates_all_models(
    language=DEFAULT_LANGUAGE,
    topic_key=DEFAULT_TOPIC,
    mode=DEFAULT_MODE,
    models=None,
    template_start=DEFAULT_TEMPLATE_START,
    template_end=DEFAULT_TEMPLATE_END,
):
    """
    Jalankan template 00001-00010 untuk beberapa model.

    - mode='zero' memakai meme_pipeline_1
    - mode='few' memakai meme_pipeline_few
    - topic dan temperature tetap di-hardcode di level pemanggilan / model file
    """
    selected_models = models or DEFAULT_MODELS
    template_ids = [f"{i:05d}" for i in range(template_start, template_end + 1)]
    all_results = {}

    for model_name in selected_models:
        print(f"\n{'=' * 70}")
        print(f"RUN MODEL: {model_name}")
        print(f"{'=' * 70}")

        try:
            runner = _load_runner(model_name, mode)
        except Exception as exc:
            print(f"[ERROR] gagal load model={model_name} -> {exc}")
            all_results[model_name] = {"_load_error": str(exc)}
            continue

        model_results = {}
        for template_id in template_ids:
            print(
                f"\n[RUN] model={model_name} | template={template_id} | "
                f"topic={topic_key} | mode={mode}"
            )
            try:
                result = runner(template_id, topic_key=topic_key, language=language)
                model_results[template_id] = result
            except Exception as exc:
                print(f"[ERROR] model={model_name} | template={template_id} -> {exc}")
                model_results[template_id] = {"error": str(exc)}

        all_results[model_name] = model_results

    return all_results


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, choices=["id", "en"])
    parser.add_argument("--mode", default=DEFAULT_MODE, choices=["zero", "few"])
    parser.add_argument("--topic", default=DEFAULT_TOPIC)
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        choices=list(MODEL_MODULES.keys()),
    )
    parser.add_argument("--start", type=int, default=DEFAULT_TEMPLATE_START)
    parser.add_argument("--end", type=int, default=DEFAULT_TEMPLATE_END)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    results = run_templates_all_models(
        language=args.language,
        topic_key=args.topic,
        mode=args.mode,
        models=args.models,
        template_start=args.start,
        template_end=args.end,
    )

    print(f"\n{'=' * 70}")
    print("RINGKASAN")
    print(f"{'=' * 70}")
    for model_name, model_results in results.items():
        if isinstance(model_results, dict) and "_load_error" in model_results:
            print(f"- {model_name}: load_error=1")
            continue

        success_count = sum(
            1 for result in model_results.values()
            if isinstance(result, dict) and "error" not in result
        )
        error_count = len(model_results) - success_count
        print(f"- {model_name}: success={success_count}, error={error_count}")
