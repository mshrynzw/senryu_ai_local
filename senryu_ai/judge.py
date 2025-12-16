import json
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
from senryu_ai.mora import is_575
from senryu_ai.llm_ollama import call_ollama

@dataclass
class ScoredItem:
    total: float
    rule: float
    llm: float
    reasons: List[str]
    item: Dict[str, Any]

def rule_score(item: Dict[str, Any]) -> Tuple[float, List[str]]:
    lines = [s.strip() for s in item.get("lines", [])]
    reasons: List[str] = []
    score = 0.0

    if len(lines) != 3:
        return -999.0, ["3行ではない"]

    if not is_575(lines):
        return -50.0, ["五七五から外れている"]
    score += 10.0
    reasons.append("五七五OK")

    joined = "".join(lines)
    if any(joined.endswith(x) for x in ["です", "ます", "でした", "ますね"]):
        score -= 2.0
        reasons.append("説明調の語尾")

    if len(set(joined)) < max(10, len(joined)//4):
        score -= 1.5
        reasons.append("単調（文字種少）")

    return score, reasons

def llm_judge(style_profile: Dict[str, Any], items: List[Dict[str, Any]]) -> List[float]:
    profile_json = json.dumps(style_profile, ensure_ascii=False)
    items_json = json.dumps(items, ensure_ascii=False)

    prompt = f"""
あなたは川柳の選者です。以下のスタイルプロファイルに照らして各候補を0〜10点で採点してください。

評価軸:
- 作者らしさ（作風一致）
- 余韻・含意
- 新規性（ありきたり回避）
- 情景の立ち上がり

【スタイルプロファイル】
{profile_json}

【候補(JSON)】
{items_json}

出力は点数のみのJSON配列。候補と同じ順序・同じ件数。
""".strip()

    text = call_ollama(prompt)
    start = text.find("[")
    end = text.rfind("]")
    scores = json.loads(text[start:end+1])
    return [float(x) for x in scores]
