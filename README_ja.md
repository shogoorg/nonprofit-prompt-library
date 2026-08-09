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
@資金調達 どんなプロンプト（タスク）が利用可能か教えてください。
@資金調達 助成金プログラムの要点を抽出して（No.03）
```