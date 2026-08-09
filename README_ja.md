# 非営利向けプロンプトライブラリ

非営利向けのプロンプトライブラリ

---

## プロジェクト構造

```text
nonprofit-prompt-library
├── data
│   └── prompts_ja.csv    
├── skills                
   　└── ja
       ├── fundraising
       │   ├── SKILL.md
       │   └── references/
       ├── marketing
       │   ├── SKILL.md
       │   └── references/
       └── program-management
           ├── SKILL.md
           └── references/

```

---

## クイックスタート

```bash
git clone https://github.com/shogoorg/nonprofit-prompt-library.git
cd nonprofit-prompt-library
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
python convert_plugin.py --lang ja
```

```bash
mkdir -p .agents
ln -s ../skills/ja .agents/skills
```

```bash
# 1. 利用可能なタスクの確認
@資金調達 どんなプロンプト（タスク）が利用可能か教えてください。

# 2. タスクの選択と詳細（プロンプト内容など）の確認
@資金調達 助成金プログラムの要点を抽出して 3 の詳細を教えてください。

# 3. タスクの実行
@資金調達 あなたは、気候アクションの資金調達の専門家です。環境保護財団（支援者）の具体的な関心事と優先事項に焦点を当てて、この地域温暖化防止活動助成金の説明の要点を抽出して。

【説明文】 （ここに助成金の募集要項テキストを貼り付ける、またはURLを入力する）
```