import json
import re
from typing import List, Dict, Any
from senryu_ai.llm_ollama import call_ollama

def build_style_profile(original_texts: List[str]) -> Dict[str, Any]:
    sample = "\n".join(f"- {s}" for s in original_texts[:200])
    prompt = f"""
あなたは川柳の編集者です。以下の川柳群から作者の作風を抽出し、
生成時に再現できる「スタイルプロファイル」をJSONで作成してください。

必須キー:
- tone: 雰囲気（例: 口語/やさしい/ユーモア等）
- themes: よく出るテーマ上位5
- diction: 語彙の特徴（抽象/具体、硬い/柔らかい等）
- imagery: 情景の傾向
- rhythm: リズムや切れの傾向
- constraints: 守るべきルール（例: 説明しすぎない 等）
- examples: 作者らしさが強い例を3つ（原文そのまま）

川柳一覧:
{sample}

出力はJSONのみ。余計な文章は禁止。
""".strip()

    text = call_ollama(prompt)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise RuntimeError(f"OllamaがJSONオブジェクトを返しませんでした。出力: {text[:200]}...")
    
    json_str = text[start:end+1]
    
    # JSONの前処理：一般的なエスケープ問題を修正
    json_str = re.sub(r'\\"\]', '"]', json_str)  # \"] を "] に修正
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        lines = json_str.split('\n')
        error_line = lines[e.lineno - 1] if 0 < e.lineno <= len(lines) else ""
        error_msg = f"JSONパースエラー: {e}\n"
        error_msg += f"エラー位置: 行 {e.lineno}, 列 {e.colno}\n"
        if error_line:
            error_msg += f"問題のある行: {error_line}\n"
            if e.colno > 0:
                error_msg += f"          {' ' * (e.colno - 1)}^\n"
        error_msg += f"\n抽出したJSON（最初の1000文字）:\n{json_str[:1000]}"
        raise RuntimeError(error_msg)
