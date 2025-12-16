import json
import re
from typing import List, Dict, Any
from senryu_ai.llm_ollama import call_ollama
from senryu_ai.config import CONFIG

def generate_candidates(style_profile: Dict[str, Any], original_texts: List[str], n: int) -> List[Dict[str, Any]]:
    profile_json = json.dumps(style_profile, ensure_ascii=False)
    seeds = "\n".join(f"- {s}" for s in original_texts[:50])

    prompt = f"""
あなたは川柳作家です。以下のスタイルプロファイルに厳密に従って川柳を作成してください。

【スタイルプロファイル(JSON)】
{profile_json}

【元の川柳（作風の参考。コピペ禁止）】
{seeds}

【重要：五七五の形式】
川柳は必ず「上5音・中7音・下5音」の形式です。
- 上句：5音（例：「スキー授業」= 5音）
- 中句：7音（例：「ゲレンデ行こう！と」= 7音）
- 下句：5音（例：「グラウンドへ」= 5音）

音数（モーラ数）の数え方：
- 通常の文字：1音
- 小文字（ゃゅょぁぃぅぇぉ）：直前の文字と合わせて1音
- 長音（ー）：1音
- 促音（っ）：1音
- 撥音（ん）：1音

要件:
- 形式は必ず3行（上/中/下）
- 上5音 / 中7音 / 下5音 を厳密に守る（これが最重要）
- 余韻・含意を重視。説明しすぎない
- ありきたり回避（定型フレーズ連発禁止）
- 出力はJSON配列のみ（余計な説明文は不要）
- 1要素の形式:
  {{"type":"new","lines":["上句（5音）","中句（7音）","下句（5音）"],"note":"狙い（短く）"}}

【重要：JSON形式について】
- 文字列内の引用符はエスケープ不要（通常の " でOK）
- 配列の最後の要素の後にもカンマを付けない
- 有効なJSON形式であることを確認してください

{n}件生成。各候補は必ず五七五の形式にしてください。
可能な限り多くの候補を生成してください（最低でも{n}件以上）。
""".strip()

    # 大量生成の場合は複数回に分ける
    batch_size = min(50, n)  # 1回あたり最大50件
    all_candidates = []
    
    if n > 50:
        # 複数回に分けて生成
        num_batches = (n + batch_size - 1) // batch_size
        print(f"大量生成のため、{num_batches}回に分けて生成します...")
        for batch_num in range(num_batches):
            current_batch_size = min(batch_size, n - len(all_candidates))
            if current_batch_size <= 0:
                break
            print(f"  バッチ {batch_num + 1}/{num_batches} ({current_batch_size}件)...")
            batch_prompt = prompt.replace(f"{n}件生成", f"{current_batch_size}件生成").replace(f"最低でも{n}件以上", f"最低でも{current_batch_size}件以上")
            
            # 再試行ロジック
            max_retries = 10
            batch_candidates = []
            for retry in range(max_retries):
                try:
                    text = call_ollama(batch_prompt)
                    batch_candidates = _parse_json_array(text, current_batch_size)
                    if batch_candidates:  # 成功した場合
                        break
                    elif retry < max_retries - 1:  # 0件でも再試行
                        print(f"    再試行 {retry + 1}/{max_retries - 1}...")
                except Exception as e:
                    max_retries = 10
                    if retry < max_retries - 1:
                        print(f"    エラー発生、再試行 {retry + 1}/{max_retries - 1}... ({str(e)[:50]})")
                    else:
                        print(f"    バッチ {batch_num + 1} は失敗しました（{max_retries}回試行後）。スキップします。")
                        batch_candidates = []
            
            if batch_candidates:
                all_candidates.extend(batch_candidates)
        return all_candidates
    else:
        # 50件以下の場合も再試行ロジックを追加
        max_retries = 10
        for retry in range(max_retries):
            try:
                text = call_ollama(prompt)
                result = _parse_json_array(text, n)
                if result:  # 成功した場合
                    return result
                elif retry < max_retries - 1:  # 0件でも再試行
                    print(f"再試行 {retry + 1}/{max_retries - 1}...")
            except Exception as e:
                max_retries = 10
                if retry < max_retries - 1:
                    print(f"エラー発生、再試行 {retry + 1}/{max_retries - 1}... ({str(e)[:50]})")
                else:
                    raise  # 最後の試行でも失敗した場合はエラーを投げる
        return []  # すべての試行が失敗した場合

def _parse_json_array(text: str, expected_count: int = 0) -> List[Dict[str, Any]]:
    """JSON配列をパースするヘルパー関数"""
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or start >= end:
        raise RuntimeError(f"OllamaがJSON配列を返しませんでした。出力: {text[:200]}...")
    
    json_str = text[start:end+1]
    
    # JSONの前処理：一般的なエスケープ問題を修正
    # 1. 制御文字を削除（改行文字以外の制御文字）
    json_str = ''.join(ch for ch in json_str if ord(ch) >= 32 or ch in '\n\r\t')
    # 2. \"] を "] に修正（文字列終端の不正なエスケープ）
    json_str = re.sub(r'\\"\]', '"]', json_str)
    # 3. 文字列内の \" を " に修正（ただし、これは慎重に）
    # 文字列リテラル内の \" を検出して修正（より安全な方法）
    # パターン: "文字列\" を "文字列" に
    json_str = re.sub(r'([^\\])\\"([^"])', r'\1"\2', json_str)  # 文字列内の \" を " に
    # 4. 行末の \ を削除（不正なエスケープ）
    json_str = re.sub(r'\\\n', '\n', json_str)
    
    # 複数回パースを試みる（修正を試みる）
    for attempt in range(5):
        try:
            result = json.loads(json_str)
            # デバッグ: パース成功時の情報
            if expected_count > 0 and len(result) == 0:
                print(f"  デバッグ: JSONパースは成功しましたが、結果が0件です。")
            # データの正規化：中句/下句が別キーの場合、lines配列に統合
            normalized_result = []
            for item in result:
                if not isinstance(item, dict):
                    continue
                # 中国語などの不正な文字が含まれている場合はスキップ（lines配列内の文字列のみチェック）
                has_chinese = False
                if "lines" in item and isinstance(item.get("lines"), list):
                    for line in item["lines"]:
                        if isinstance(line, str) and re.search(r'[\u4e00-\u9fff]', line):
                            has_chinese = True
                            break
                if has_chinese:
                    continue
                # linesが配列でない、または中句/下句が存在する場合
                if "lines" not in item or not isinstance(item.get("lines"), list):
                    # 中句と下句からlinesを構築
                    if "中句" in item and "下句" in item:
                        lines = []
                        if "lines" in item and isinstance(item["lines"], list) and len(item["lines"]) > 0:
                            lines.append(item["lines"][0])
                        else:
                            lines.append("")  # 上句が不明
                        if isinstance(item["中句"], list):
                            lines.extend(item["中句"])
                        else:
                            lines.append(item["中句"])
                        if isinstance(item["下句"], list):
                            lines.extend(item["下句"])
                        else:
                            lines.append(item["下句"])
                        item["lines"] = lines
                        del item["中句"]
                        del item["下句"]
                    elif "lines" not in item:
                        continue  # linesがない場合はスキップ
                # linesが3要素でない場合の処理
                if isinstance(item.get("lines"), list) and len(item["lines"]) != 3:
                    # 1要素で全角スペースで区切られている場合、分割を試みる
                    if len(item["lines"]) == 1:
                        single_line = item["lines"][0]
                        # 全角スペースで分割（2つ以上）
                        parts = [p.strip() for p in single_line.split("　") if p.strip()]
                        if len(parts) >= 3:
                            item["lines"] = parts[:3]
                        elif len(parts) == 2:
                            item["lines"] = parts + [""]
                        elif len(parts) == 1:
                            # 全角スペースがない場合、半角スペースで試す
                            parts = [p.strip() for p in single_line.split() if p.strip()]
                            if len(parts) >= 3:
                                item["lines"] = parts[:3]
                            elif len(parts) == 2:
                                item["lines"] = parts + [""]
                            else:
                                # 分割できない場合、空文字で埋める
                                item["lines"] = [single_line, "", ""]
                    # 可能な限り修正を試みる
                    if len(item["lines"]) > 3:
                        item["lines"] = item["lines"][:3]
                    elif len(item["lines"]) < 3:
                        # 不足分を空文字で埋める
                        while len(item["lines"]) < 3:
                            item["lines"].append("")
                normalized_result.append(item)
            
            # 生成数が少ない場合に警告
            if expected_count > 0 and len(normalized_result) < expected_count * 0.1:  # 要求の10%未満の場合
                print(f"警告: 要求数 {expected_count} 件に対して {len(normalized_result)} 件しか生成されませんでした。")
                if len(result) > len(normalized_result):
                    print(f"  デバッグ: 元のJSONには {len(result)} 件ありましたが、{len(result) - len(normalized_result)} 件がフィルタリングで除外されました。")
            return normalized_result
        except json.JSONDecodeError as e:
            if attempt == 4:  # 最後の試行（0-4なので4が最後）
                # 最後の手段：部分的なパースを試みる
                try:
                    # エラー位置より前の部分だけをパース
                    error_pos = e.pos if hasattr(e, 'pos') else len(json_str)
                    # エラー位置より前で、最後の完全なオブジェクトを見つける
                    partial_json = json_str[:error_pos]
                    # 最後の完全なオブジェクトの終わりを見つける
                    last_brace = partial_json.rfind('}')
                    if last_brace > 0:
                        # 最後の完全なオブジェクトまでを抽出
                        partial_json = json_str[:last_brace + 1]
                        # 配列を閉じる
                        if not partial_json.rstrip().endswith(']'):
                            partial_json = partial_json.rstrip().rstrip(',') + ']'
                        # 部分的なパースを試みる
                        partial_result = json.loads(partial_json)
                        normalized_result = []
                        for item in partial_result:
                            if isinstance(item, dict) and "lines" in item and isinstance(item.get("lines"), list):
                                if len(item["lines"]) == 3:
                                    normalized_result.append(item)
                        if normalized_result:
                            print(f"警告: 部分的なパースに成功しました（{len(normalized_result)}件）。エラー位置以降はスキップされました。")
                            return normalized_result
                except Exception:
                    pass
                
                # エラーの詳細を表示
                lines = json_str.split('\n')
                error_line = lines[e.lineno - 1] if 0 < e.lineno <= len(lines) else ""
                error_msg = f"JSONパースエラー（{attempt + 1}回試行後）: {e}\n"
                error_msg += f"エラー位置: 行 {e.lineno}, 列 {e.colno}\n"
                if error_line:
                    error_msg += f"問題のある行: {error_line}\n"
                    if e.colno > 0:
                        error_msg += f"          {' ' * (e.colno - 1)}^\n"
                error_msg += f"\n抽出したJSON（最初の1000文字）:\n{json_str[:1000]}"
                raise RuntimeError(error_msg)
            # 追加の修正を試みる
            if attempt == 0:
                # より積極的な修正：文字列内のすべての \" を " に
                json_str = json_str.replace('\\"', '"')
                # 連結されたオブジェクトを修正（例: }{" → },{）
                json_str = re.sub(r'\}\s*\{', r'}, {', json_str)
                # より具体的なパターン: "note":"..."}{" → "note":"..."}, {"
                json_str = re.sub(r'"note":\s*"([^"]*)"\}\{', r'"note":"\1"}, {', json_str)
                # lines配列内の余分なカンマを削除（例: "蝶",] → "蝶"]）
                json_str = re.sub(r'",\s*\]', r'"]', json_str)
                # 配列の要素の閉じ括弧が間違っている場合を修正（例: }], → },）
                json_str = re.sub(r'\}\],\s*', r'}, ', json_str)
                json_str = re.sub(r'\}\],\s*$', r'}', json_str)
                # lines配列が閉じられていない場合を修正（例: "寒さに", "note" → "寒さに"], "note"）
                json_str = re.sub(r'("lines":\[[^\]]*)"([^"]+)",\s*"note"', r'\1"\2"], "note"', json_str)
            elif attempt == 1:
                # 不正なカンマを修正（例: }, "note" → , "note"）
                json_str = re.sub(r'\},\s*"note"', r', "note"', json_str)
                json_str = re.sub(r'\},\s*"type"', r', "type"', json_str)
                # 余分なカンマと閉じ括弧を修正（例: "note":"遊び"], → "note":"遊び"}）
                json_str = re.sub(r'"note":\s*"([^"]*)"\],\s*', r'"note":"\1"}', json_str)
                # 閉じ括弧の前に余分なカンマがある場合を修正
                json_str = re.sub(r'"([^"]*)"\],\s*"note"', r'"\1", "note"', json_str)
                # }, "note":"..."], の形式を , "note":"..."} に修正
                json_str = re.sub(r'\},\s*"note":\s*"([^"]*)"\],\s*', r', "note":"\1"}', json_str)
                # 閉じ括弧が ) になっている場合を修正（例: "note":"..."), → "note":"..."}）
                json_str = re.sub(r'"note":\s*"([^"]*)"\)\s*,', r'"note":"\1"},', json_str)
                json_str = re.sub(r'"note":\s*"([^"]*)"\)\s*$', r'"note":"\1"}', json_str)
                # lines配列が閉じられていない場合を修正
                # パターン: "lines":["...", "...", "...", "note" → "lines":["...", "...", "..."], "note"
                # 行単位で処理（より確実）
                lines_list = json_str.split('\n')
                fixed_lines = []
                for line in lines_list:
                    # "lines":[... で始まり、その中に ", "note" がある場合
                    if '"lines":[' in line:
                        # パターン1: "lines":["...", "...", "...", "note" → "lines":["...", "...", "..."], "note"
                        if ', "note"' in line and '], "note"' not in line:
                            # 最後の ", "note" の前に ] を挿入
                            # より積極的な修正：配列内の最後の要素の後に "note" が来る場合
                            line = re.sub(r'("lines":\[[^\]]*)"([^"]+)",\s*"note"', r'\1"\2"], "note"', line)
                            # より単純なパターン: 配列内の要素の後に直接"note"が来る場合
                            line = re.sub(r'("([^"]+)"),\s*"note"', r'\1], "note"', line, count=1)
                        # パターン2: "lines":["...", "...", "..."}{"type" → "lines":["...", "...", "..."], "type" は存在しないが、連結されたオブジェクトを修正
                        # 連結されたオブジェクトを修正（例: "note":"..."}{"type" → "note":"..."}, {"type"）
                        if '"note"' in line and '}{' in line:
                            # "note":"..."}{" の前に }, を挿入
                            line = re.sub(r'"note":\s*"([^"]*)"\}\{', r'"note":"\1"}, {', line)
                    fixed_lines.append(line)
                json_str = '\n'.join(fixed_lines)
            elif attempt == 2:
                # 不正なエスケープシーケンスを削除
                json_str = re.sub(r'\\(?![\\/bfnrt"u])', '', json_str)
                # 連結されたオブジェクトを修正（例: }{" → },{）
                json_str = re.sub(r'\}\s*\{', r'}, {', json_str)
                # lines配列内の余分なカンマを削除（例: "蝶",] → "蝶"]）
                json_str = re.sub(r'",\s*\]', r'"]', json_str)
                # 配列内の最後の要素の後にカンマがある場合を削除（例: "蝶",] → "蝶"]）
                json_str = re.sub(r'("([^"]+)"),\s*\]', r'\1]', json_str)
            elif attempt == 3:
                # 不完全なJSONエントリを修正
                # 閉じ括弧が欠けている場合を検出して追加
                # 開き括弧と閉じ括弧の数を数えて修正
                open_braces = json_str.count('{')
                close_braces = json_str.count('}')
                if open_braces > close_braces:
                    # 不足分の閉じ括弧を追加（最後に）
                    json_str = json_str.rstrip().rstrip(']') + '}' * (open_braces - close_braces) + ']'
                # 不完全な文字列を検出して修正（例: "note":"冬季 → "note":"冬季"）
                json_str = re.sub(r'"note":\s*"([^"]*?)(?:"|,|\}|\])', r'"note":"\1"', json_str)
                # 最後の不完全なエントリを削除（例: {"lines":["...","...","冬遊 → 削除）
                # 閉じ括弧がない行を削除
                lines_list = json_str.split('\n')
                fixed_lines = []
                for line in lines_list:
                    # 開き括弧があるが閉じ括弧がない行をスキップ
                    if '{' in line and '}' not in line:
                        # 不完全な行なのでスキップ
                        continue
                    # 中国語などの不正な文字が含まれている行をスキップ
                    # ただし、文字列リテラル内（"..."）の中国語のみをチェック
                    # JSONの構造部分は除外
                    in_string = False
                    has_chinese_in_string = False
                    i = 0
                    while i < len(line):
                        if line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                            in_string = not in_string
                        elif in_string and re.match(r'[\u4e00-\u9fff]', line[i]):
                            has_chinese_in_string = True
                            break
                        i += 1
                    if has_chinese_in_string:
                        # 文字列リテラル内に中国語が含まれている行をスキップ
                        continue
                    fixed_lines.append(line)
                json_str = '\n'.join(fixed_lines)
                # 最後の不完全なエントリを削除（正規表現でも）
                json_str = re.sub(r',\s*\{[^}]*$', '', json_str)
                # 最後のカンマを削除（例: }, → }）
                json_str = re.sub(r',\s*$', '', json_str.rstrip())
                # 最後に ] を追加（もし欠けている場合）
                if not json_str.rstrip().endswith(']'):
                    json_str = json_str.rstrip().rstrip(',') + ']'
            elif attempt == 4:
                # 最後の試行：より積極的な修正
                # 不完全なエントリを削除（例: {"lines":["...","...","} → 削除）
                json_str = re.sub(r',\s*\{[^}]*$', '', json_str)
                # 連結されたオブジェクトを修正（例: }{" → },{）
                json_str = re.sub(r'\}\s*\{', r'}, {', json_str)
                # 不完全な文字列を削除（例: "note":"... → 削除）
                json_str = re.sub(r',\s*"note":\s*"[^"]*$', '', json_str)
                # 最後のカンマを削除
                json_str = re.sub(r',\s*$', '', json_str.rstrip())
                # 最後に ] を追加（もし欠けている場合）
                if not json_str.rstrip().endswith(']'):
                    json_str = json_str.rstrip().rstrip(',') + ']'
