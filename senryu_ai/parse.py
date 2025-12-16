import re
from typing import List, Dict, Any

def split_senryu_line(raw: str) -> List[str]:
    """
    入力行を上中下に分割する。
    優先順:
      1) "/" 区切り（手動整形に便利）
      2) 全角/半角スペース連続で分割
    期待: 3要素（上・中・下）
    """
    raw = raw.strip()
    if "/" in raw:
        parts = [p.strip() for p in raw.split("/") if p.strip()]
        return parts

    parts = re.split(r"[ 　]+", raw)  # 半角/全角スペース
    parts = [p for p in parts if p]
    return parts

def load_originals(path: str) -> List[Dict[str, Any]]:
    """
    originals.txt から読み込み。
    返り値は:
      [{"raw": 原文, "lines": ["上","中","下"]}, ...]
    """
    originals: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f.read().splitlines():
            raw = line.strip()
            if not raw:
                continue
            parts = split_senryu_line(raw)
            if len(parts) != 3:
                # 形式崩れはスキップ（必要ならログ出してもOK）
                continue
            originals.append({"raw": raw, "lines": parts})
    return originals
