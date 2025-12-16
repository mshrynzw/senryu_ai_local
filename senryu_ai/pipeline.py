import os
import json
from typing import List, Dict, Any
from senryu_ai.config import CONFIG
from senryu_ai.parse import load_originals
from senryu_ai.style import build_style_profile
from senryu_ai.generate import generate_candidates
from senryu_ai.judge import rule_score, llm_judge, ScoredItem

def run_pipeline(
    originals_path: str = "originals.txt",
    out_dir: str = "out",
) -> None:
    os.makedirs(out_dir, exist_ok=True)

    originals = load_originals(originals_path)
    if len(originals) < 10:
        print("注意：10句未満だと作風抽出が弱くなります（100句あるなら理想）")

    original_texts = [o["raw"] for o in originals]

    # 1) 作風抽出
    style_profile = build_style_profile(original_texts)
    with open(os.path.join(out_dir, "style_profile.json"), "w", encoding="utf-8") as f:
        json.dump(style_profile, f, ensure_ascii=False, indent=2)

    # 2) 生成（量産）
    candidates = generate_candidates(style_profile, original_texts, CONFIG.n_generate)
    print(f"生成された候補数: {len(candidates)}")

    # 3) ルール採点・足切り
    ok_items: List[Dict[str, Any]] = []
    rule_meta: List[tuple[Dict[str, Any], float, list[str]]] = []
    rejected_samples: List[tuple[Dict[str, Any], float, list[str]]] = []
    for it in candidates:
        r, reasons = rule_score(it)
        if r > -10:  # 五七五NGなどを落とす
            ok_items.append(it)
            rule_meta.append((it, r, reasons))
        else:
            # デバッグ用：最初の3件のNG候補を保存
            if len(rejected_samples) < 3:
                rejected_samples.append((it, r, reasons))

    if not ok_items:
        print(f"\n五七五OKの候補が出ませんでした（生成数: {len(candidates)}件）。")
        if rejected_samples:
            print("\n【NG候補の例（最初の3件）】")
            for i, (it, r, reasons) in enumerate(rejected_samples, 1):
                lines = it.get("lines", [])
                print(f"{i}. score={r:.1f}, reasons={', '.join(reasons)}")
                if lines:
                    print(f"   {lines}")
                else:
                    print(f"   {it}")
        print("\n対処法:")
        print("1. N_GENERATEを増やす（例: $env:N_GENERATE=\"500\"）")
        print("2. モデルを変える（例: $env:OLLAMA_MODEL=\"llama3.2:3b\"）")
        print("3. originals.txtに10句以上追加する（100句が理想）")
        return

    # 4) LLM採点（任意）
    if CONFIG.enable_llm_judge:
        llm_scores = llm_judge(style_profile, ok_items)
    else:
        llm_scores = [0.0 for _ in ok_items]

    # 5) 合算して並べる
    merged: List[ScoredItem] = []
    for (it, r, reasons), ls in zip(rule_meta, llm_scores):
        total = r + float(ls)
        merged.append(ScoredItem(total=total, rule=r, llm=float(ls), reasons=reasons, item=it))

    merged.sort(key=lambda x: x.total, reverse=True)
    keep = merged[: CONFIG.n_keep]

    # 6) 出力
    out_json = [
        {
            "total": k.total,
            "rule": k.rule,
            "llm": k.llm,
            "type": k.item.get("type"),
            "lines": k.item.get("lines"),
            "note": k.item.get("note", ""),
            "reasons": k.reasons,
        }
        for k in keep
    ]

    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(out_json, f, ensure_ascii=False, indent=2)

    md: List[str] = ["# 川柳AI（ローカル）上位結果\n"]
    for i, k in enumerate(out_json, 1):
        md.append(f"## {i}. score={k['total']:.2f} (rule={k['rule']:.1f}, llm={k['llm']:.1f})")
        md.extend([f"- {k['lines'][0]}", f"- {k['lines'][1]}", f"- {k['lines'][2]}"])
        if k["note"]:
            md.append(f"- note: {k['note']}")
        if k["reasons"]:
            md.append(f"- reasons: {', '.join(k['reasons'])}")
        md.append("")

    with open(os.path.join(out_dir, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"Done! {os.path.join(out_dir, 'results.md')} を確認してください。")
