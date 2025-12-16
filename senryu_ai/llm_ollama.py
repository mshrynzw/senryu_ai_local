import ollama
from senryu_ai.config import CONFIG

def list_available_models() -> list[str]:
    """利用可能なOllamaモデルのリストを取得"""
    try:
        models = ollama.list()
        return [model["name"] for model in models.get("models", [])]
    except Exception:
        return []

def call_ollama(prompt: str) -> str:
    """
    Ollamaをローカル実行（APIキー不要）。
    事前に `ollama pull <model>` 済みであること。
    Ollamaサーバーが起動している必要があります。
    """
    try:
        response = ollama.generate(
            model=CONFIG.ollama_model,
            prompt=prompt,
        )
        return response["response"].strip()
    except Exception as e:
        error_msg = str(e)
        # モデルが見つからない場合の特別な処理
        if "not found" in error_msg.lower() or "404" in error_msg:
            available = list_available_models()
            msg = f"\nモデル '{CONFIG.ollama_model}' が見つかりません。\n\n"
            if available:
                msg += f"利用可能なモデル:\n"
                for m in available:
                    msg += f"  - {m}\n"
                msg += f"\nモデルをインストールするには:\n"
                msg += f"  ollama pull {CONFIG.ollama_model}\n"
                msg += f"\nまたは、利用可能なモデルを使用するには:\n"
                msg += f"  $env:OLLAMA_MODEL=\"{available[0] if available else 'qwen2.5:7b-instruct'}\"\n"
            else:
                msg += "利用可能なモデルが見つかりませんでした。\n"
                msg += f"モデルをインストールしてください:\n"
                msg += f"  ollama pull {CONFIG.ollama_model}\n"
            raise RuntimeError(msg)
        raise RuntimeError(f"Ollama error: {e}")
