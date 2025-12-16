# senryu_ai_local  
完全ローカルで動作する「川柳生成AI」プロジェクト  
（APIキー不要 / ChatGPT不要 / Ollama使用）


---

## これは何？
このプロジェクトは、

- **川柳（例：100句）を読み込み**
- **作者の作風を自動で分析し**
- **その作風を真似した新しい川柳を大量に生成**
- **五七五になっていない句を自動で除外**
- **良い句だけを自動採点して上位を出力**

する、**完全ローカル動作の川柳AI**です。

### 特徴
- 🔒 **外部API・APIキー不要**
- 🖥 **すべて自分のPC内で完結**
- 🇯🇵 **日本語特化（川柳向け）**
- ⚙ **Pythonのみで構成**
- 🎯 「量産 → 自動選別」で実用的な品質を確保


---

## 動作イメージ（流れ）

```
originals.txt（あなたの川柳100句）
↓
作風分析（ローカルLLM）
↓
川柳を大量生成（300件など）
↓
五七五チェック（自動）
↓
自動採点（ルール＋AI）
↓
上位川柳だけを出力（results.md）

````

あなたは **川柳を用意して実行するだけ**です。

---

## 必要なもの

### 1. ハードウェア
- Windows 11
- メモリ 16GB以上（32GB以上推奨）
- NVIDIA GPU（あれば高速。なくても可）

### 2. ソフトウェア
- **Python 3.10 以上**
- **Ollama（ローカルLLM実行環境）**

---

## セットアップ手順（初回のみ）

### Step 1. Ollama本体（サーバー）をインストール
- https://ollama.com/download から Windows版をインストール
- **重要**: これはOllamaサーバー本体です（コマンドラインの `ollama` コマンドが使えるようになります）

インストール後、PowerShellで確認：

```powershell
ollama --version
```

**もし `ollama` コマンドが認識されない場合**：

Ollamaはインストールされているが、PATHに追加されていない可能性があります。以下のいずれかの方法で対処できます：

**方法1: フルパスで実行（一時的）**
```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull qwen2.5:7b-instruct
```

**方法2: PATHに追加（推奨）**
1. Windowsの設定 → システム → 詳細情報 → システムの詳細設定
2. 「環境変数」をクリック
3. 「システム環境変数」の「Path」を選択して「編集」
4. 「新規」をクリックして以下を追加：
   ```
   %LOCALAPPDATA%\Programs\Ollama
   ```
5. PowerShellを再起動

> **注意**: `pip install ollama` だけでは不十分です。Ollama本体（サーバー）をインストールする必要があります。

---

### Step 2. 使用するローカルLLMを取得

川柳用途では以下がおすすめです。

**PATHに追加済みの場合：**
```powershell
ollama pull qwen2.5:7b-instruct
```

**PATHに追加されていない場合：**
```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull qwen2.5:7b-instruct
```

動作確認：

**PATHに追加済みの場合：**
```powershell
ollama run qwen2.5:7b-instruct
```

**PATHに追加されていない場合：**
```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" run qwen2.5:7b-instruct
```

日本語で返答があれば成功。
終了は `Ctrl + D`。

---

### Step 3. Python 仮想環境を作成

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

---

### Step 4. Python依存ライブラリをインストール

```powershell
pip install -r requirements.txt
```

これにより以下がインストールされます：
- `pyopenjtalk`: 五七五判定がより正確になります（入らなくても簡易判定で動作）
- `ollama`: PythonからOllama APIを呼び出すためのライブラリ

---

## originals.txt の書き方（重要）

### 書式ルール

* **1行に1句**
* **全角スペース2つで区切る**
* 上五・中七・下五の順

### 例

```txt
冬休み　スキー場行くよと　雪降らず
学校で　雪合戦しようと　雨が降る
友達と　アイススケートと　リンク閉鎖
```

### 注意

* 行番号や「・」「①」などは付けない
* 余計なコメントは書かない
* 100句あると理想的

---

## 実行方法

プロジェクト直下で：

```powershell
python main.py
```

初回は数分かかることがあります。

---

## 出力ファイルの説明

実行後、`out/` フォルダが作成されます。

```
out/
 ├─ style_profile.json
 ├─ results.json
 └─ results.md
```

### style_profile.json

* あなたの川柳から抽出された「作風」
* 人が読む必要はありません（参考用）

### results.md（←ここを見る）

* AIが生成した川柳の **上位結果**
* 採点付き
* 提出・推敲用の成果物

### results.json

* 機械処理用（後で再利用したい場合）

---

## よくあるトラブル

### Q. results.md が空 / 出ない

* originals.txt の形式が崩れている可能性
* 全角スペースが2つあるか確認

### Q. 「五七五OKの候補が出ませんでした」と表示される

このエラーは、生成された川柳が五七五の形式に合致していない場合に発生します。

**原因と対処法：**

1. **originals.txtの句数が少ない**
   - 10句未満だと作風抽出が弱くなります
   - 100句以上あると理想的です

2. **生成数が少ない**
   ```powershell
   $env:N_GENERATE="500"
   python main.py
   ```

3. **モデルが五七五を理解していない**
   - 別のモデルを試す（例：`llama3.2`、`llama3.1:8b`）
   ```powershell
   $env:OLLAMA_MODEL="llama3.2"
   python main.py
   ```
   - 利用可能なモデルを確認：
   ```powershell
   ollama list
   ```

4. **デバッグ情報を確認**
   - エラーメッセージにNG候補の例が表示されます
   - どのような形式で生成されているか確認できます

### Q. 五七五が崩れている

* ローカルLLMの特性です
* `config.py` の `n_generate` を増やしてください（300→500）

### Q. 遅い

* 初回はモデル読み込みで時間がかかります
* 2回目以降は速くなります
* GPUがある場合は自動で使われます

---

## 設定変更（必要になったら）

### 生成数を増やす（品質UP）

```powershell
$env:N_GENERATE="500"
python main.py
```

### 出力件数を減らす

```powershell
$env:N_KEEP="10"
python main.py
```

### 採点を高速化（ルールのみ）

```powershell
$env:ENABLE_LLM_JUDGE="0"
python main.py
```

### モデルを変更する

```powershell
# 利用可能なモデルを確認
ollama list

# モデルをインストール（例：llama3.2）
ollama pull llama3.2

# 環境変数でモデルを指定
$env:OLLAMA_MODEL="llama3.2"
python main.py
```

> **注意**: モデル名は正確に入力してください。存在しないモデル名を指定するとエラーになります。

---

## このプロジェクトで使っている考え方（簡単に）

* **深層学習（LLM）**：言葉の雰囲気・余韻・作風を真似る
* **ルールベース**：五七五を保証
* **量産→選別**：ローカルAIの弱点を補う

難しい理論を理解しなくても使えます。

---

## 次にできる拡張（将来）

* 既存句1つを徹底的に磨く「ブラッシュアップ専用モード」
* テーマ縛り（学校・冬・北海道など）
* 類似句の自動除外
* ひらがな生成 → 漢字変換で五七五精度UP

---

## 最後に

このプロジェクトは、

> **「自分の川柳を、AIの力で少しだけ磨く」**

ための道具です。
すべてローカルなので、安心して何度でも試してください。
