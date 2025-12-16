from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Config:
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    # 量産→選抜がローカルLLMでは効くので、最初は多め推奨
    n_generate: int = int(os.getenv("N_GENERATE", "300"))
    n_keep: int = int(os.getenv("N_KEEP", "30"))
    # LLMの生成ゆらぎ
    temperature: float = float(os.getenv("TEMPERATURE", "0.9"))
    # LLM採点を使うか（遅い場合Falseにしてルール採点だけでもOK）
    enable_llm_judge: bool = os.getenv("ENABLE_LLM_JUDGE", "1") not in ("0", "false", "False")

CONFIG = Config()
