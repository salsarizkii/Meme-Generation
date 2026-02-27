import llama4
import qwen3_vl
import gemma3


def run_templates_001_010_zeroshot_lecturer_all_models(language="id"):
    """
    Jalankan zero-shot untuk topic 'lecturer' pada template 001-010
    di seluruh model: llama4, qwen3-vl, gemma3.

    Notes:
    - Template akan dipanggil sebagai 5 digit: 00001 ... 00010
    - Menggunakan fungsi `meme_pipeline_1` dari masing-masing modul
    """
    model_runners = [
        ("llama4", llama4.meme_pipeline_1),
        ("qwen3-vl", qwen3_vl.meme_pipeline_1),
        ("gemma3", gemma3.meme_pipeline_1),
    ]

    template_ids = [f"{i:05d}" for i in range(1, 11)]
    all_results = {}

    for model_name, runner in model_runners:
        print(f"\n{'=' * 70}")
        print(f"RUN MODEL: {model_name}")
        print(f"{'=' * 70}")

        model_results = {}
        for template_id in template_ids:
            print(f"\n[RUN] model={model_name} | template={template_id} | topic=lecturer | mode=zero-shot")
            try:
                result = runner(template_id, topic_key="lecturer", language=language)
                model_results[template_id] = result
            except Exception as e:
                print(f"[ERROR] model={model_name} | template={template_id} -> {e}")
                model_results[template_id] = {"error": str(e)}

        all_results[model_name] = model_results

    return all_results


if __name__ == "__main__":
    results = run_templates_001_010_zeroshot_lecturer_all_models(language="id")

    print(f"\n{'=' * 70}")
    print("RINGKASAN")
    print(f"{'=' * 70}")
    for model_name, model_results in results.items():
        success_count = sum(1 for r in model_results.values() if isinstance(r, dict) and "error" not in r)
        error_count = len(model_results) - success_count
        print(f"- {model_name}: success={success_count}, error={error_count}")
