import re
from typing import List

_SMALL = set("ャュョァィゥェォヮゃゅょぁぃぅぇぉゎ")
_LONG = set("ー")
_SOKUON = set("ッっ")
_N = set("ンん")

def _count_mora_from_kana(kana: str) -> int:
    mora = 0
    for ch in kana:
        if ch in _SMALL:
            continue
        if ch in _LONG or ch in _SOKUON or ch in _N:
            mora += 1
            continue
        mora += 1
    return mora

def count_mora(text: str) -> int:
    """
    pyopenjtalk が使えれば高精度。
    使えなければかな抽出で簡易推定。
    """
    try:
        import pyopenjtalk  # type: ignore
        kana = pyopenjtalk.g2p(text, kana=True)
        return _count_mora_from_kana(kana)
    except Exception:
        kana = "".join(re.findall(r"[ぁ-ゖァ-ヺーッっんン]", text))
        if not kana:
            return max(1, len(text))
        return _count_mora_from_kana(kana)

def mora_pattern(lines: List[str]) -> List[int]:
    return [count_mora(s.strip()) for s in lines]

def is_575(lines: List[str]) -> bool:
    if len(lines) != 3:
        return False
    return mora_pattern(lines) == [5, 7, 5]
