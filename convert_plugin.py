import argparse
import glob
import json
import os
import re
import sys
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


def load_mapping(mapping_filepath):
    """Load external mapping configuration file"""
    if os.path.exists(mapping_filepath):
        with open(mapping_filepath, 'r', encoding='utf-8') as f:
            console.print(
                f'[green]✔[/green] Loaded configuration file "{mapping_filepath}".'
            )
            return json.load(f)
    console.print(
        f'[yellow]![/yellow] "{mapping_filepath}" not found, using dynamic slug generation.'
    )
    return {'categories': {}, 'tasks': {}}


def sanitize_slug(text):
    """Remove non-alphanumeric characters and convert to lower kebab-case"""
    clean_text = (
        re.sub(r'[^a-zA-Z0-9]+', '-', str(text).strip()).strip('-').lower()
    )
    return clean_text or 'task'


def resolve_csv_filepath(lang_code, custom_csv_path=None):
    """Automatically search for the input CSV file path"""
    if custom_csv_path and os.path.exists(custom_csv_path):
        return custom_csv_path

    filename = 'prompts_ja.csv' if lang_code == 'ja' else 'prompts.csv'
    path_data = os.path.join('data', filename)

    if os.path.exists(path_data):
        return path_data
    if os.path.exists(filename):
        return filename

    data_csvs = glob.glob(os.path.join('data', '*.csv'))
    if data_csvs:
        return data_csvs[0]

    root_csvs = glob.glob('*.csv')
    if root_csvs:
        return root_csvs[0]

    return None


def build_agent_plugin(
    csv_file_path,
    lang_code='ja',
    mapping_file_path=None,
    output_dir='.',
):
    if mapping_file_path is None:
        mapping_file_path = f'mapping_{lang_code}.json'
    mapping = load_mapping(mapping_file_path)
    category_map = mapping.get('categories', {})
    task_map = mapping.get('tasks', {})

    skills_root = os.path.join(output_dir, 'skills', lang_code)
    os.makedirs(skills_root, exist_ok=True)

    # Read CSV with pandas and automatically clean BOM/whitespace
    try:
        df = pd.read_csv(csv_file_path, encoding='utf-8-sig').fillna('')
        df.columns = [
            str(col).strip().replace('\ufeff', '') for col in df.columns
        ]
    except Exception as e:
        console.print(f'[bold red]Error: Failed to read CSV file:[/bold red] {e}')
        sys.exit(1)

    # Detect required columns (supports both Japanese and English headers)
    cat_col = next((c for c in df.columns if any(x in str(c).lower() for x in ['category', 'カテゴリ'])), df.columns[0])
    task_col = next((c for c in df.columns if any(x in str(c).lower() for x in ['task', 'タスク'])), df.columns[1])
    tool_col = next(
        (c for c in df.columns if any(x in str(c).lower() for x in ['tool', 'ツール'])),
        df.columns[2] if len(df.columns) > 2 else '',
    )
    prompt_col = next(
        (c for c in df.columns if any(x in str(c).lower() for x in ['prompt', 'プロンプト'])),
        df.columns[3] if len(df.columns) > 3 else '',
    )
    impact_col = next(
        (c for c in df.columns if any(x in str(c).lower() for x in ['impact', 'インパクト'])),
        df.columns[4] if len(df.columns) > 4 else '',
    )

    category_data = {}
    total_prompts = 0

    for _, row in df.iterrows():
        category = str(row.get(cat_col, '')).strip() or 'Other'
        task = str(row.get(task_col, '')).strip() or 'Task'
        tool = (
            str(row.get(tool_col, '')).strip() if tool_col else 'Unspecified'
        ) or 'Unspecified'
        prompt = (
            str(row.get(prompt_col, '')).strip() if prompt_col else ''
        ) or ''
        impact = (
            str(row.get(impact_col, '')).strip() if impact_col else ''
        ) or ''

        if not prompt:
            continue

        if category not in category_data:
            category_data[category] = []

        category_data[category].append(
            {'task': task, 'tool': tool, 'prompt': prompt, 'impact': impact}
        )
        total_prompts += 1

    with Progress(
        SpinnerColumn(),
        TextColumn('[progress.description]{task.description}'),
        console=console,
    ) as progress:
        task_id = progress.add_task(
            description='[cyan]Building Agent Plugin skills...', total=None
        )

        for category_name, items in category_data.items():
            # Get English directory name from mapping
            dir_name = category_map.get(
                category_name, sanitize_slug(category_name)
            )

            cat_dir = os.path.join(skills_root, dir_name)
            ref_dir = os.path.join(cat_dir, 'references')
            os.makedirs(ref_dir, exist_ok=True)

            index_list = []
            task_slug_counters = {}

            for i, item in enumerate(items, start=1):
                task_name = item['task']
                task_slug = task_map.get(task_name, sanitize_slug(task_name))

                task_slug_counters[task_slug] = (
                    task_slug_counters.get(task_slug, 0) + 1
                )
                sub_seq = task_slug_counters[task_slug]

                ref_filename = f'{task_slug}-{sub_seq:02d}.md'
                ref_filepath = os.path.join(ref_dir, ref_filename)

                task_label = 'タスク' if lang_code == 'ja' else 'Task'
                tool_label = 'ツール' if lang_code == 'ja' else 'Tool'
                impact_label = 'インパクト' if lang_code == 'ja' else 'Impact'
                prompt_label = 'プロンプト' if lang_code == 'ja' else 'Prompt'

                ref_content = f"""# {task_label}: {task_name} (No.{sub_seq:02d})

## 1. {task_label}
{task_name}

## 2. {tool_label}
{item['tool']}

## 3. {prompt_label}

{item['prompt']}

## 4. {impact_label}
{item['impact'] if item['impact'] else ("記述なし" if lang_code == 'ja' else "N/A")}
"""
                with open(ref_filepath, 'w', encoding='utf-8') as rf:
                    rf.write(ref_content)

                index_list.append(
                    f"- **{task_name} (No.{sub_seq:02d})** (`references/{ref_filename}`)"
                )

            skill_md_path = os.path.join(cat_dir, 'SKILL.md')
            
            # Write language-specific description in SKILL.md
            if lang_code == 'ja':
                desc_text = f"ユーザーの目的に応じて、`references/` ディレクトリ内の該当タスクファイルを参照して実行してください。"
                ref_header = "タスク参照インデックス (References)"
            else:
                desc_text = f"Please refer to the corresponding task file in the `references/` directory based on the user's objective."
                ref_header = "References"

            skill_md_content = f"""---
name: {category_name}
description: {category_name}
---

# {category_name} ({dir_name}) - [{lang_code.upper()}]

{desc_text}

## {ref_header}

""" + '\n'.join(
                index_list
            ) + '\n'

            with open(skill_md_path, 'w', encoding='utf-8') as sf:
                sf.write(skill_md_content)

        progress.update(
            task_id, completed=True, description='[green]Build complete!'
        )

    table = Table(
        title=f'Build Result Summary [{lang_code.upper()}]', show_header=True
    )
    table.add_column('Category', style='cyan')
    table.add_column('Slug', style='green')
    table.add_column('Prompts Generated', justify='right', style='magenta')

    for cat_name, items in category_data.items():
        slug = category_map.get(cat_name, sanitize_slug(cat_name))
        table.add_row(cat_name, slug, f'{len(items)}' if lang_code == 'en' else f'{len(items)} 件')

    console.print('\n')
    console.print(
        Panel.fit(
            f'[bold green]Agent Plugin package built successfully![/bold green]\n'
            f'Data Source: [bold]{csv_file_path}[/bold]\n'
            f'Language: [bold]{lang_code.upper()}[/bold] | Total Prompts: [bold]{total_prompts}[/bold]',
            title='SUCCESS',
            border_style='green',
        )
    )
    console.print(table)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Build Agent Plugin for nonprofit prompts.'
    )
    parser.add_argument(
        '--lang',
        default='ja',
        help='Target language (default: ja, options: ja, en)',
    )
    parser.add_argument(
        '--csv',
        default=None,
        help='Path to custom input CSV file',
    )
    args = parser.parse_args()

    lang_input = str(args.lang).strip().lower()
    target_lang = (
        'ja' if lang_input in ['ja', 'jp', '日本語', 'japanese'] else 'en'
    )

    csv_file = resolve_csv_filepath(target_lang, args.csv)

    if csv_file:
        build_agent_plugin(csv_file, lang_code=target_lang)
    else:
        console.print(
            '[bold red]Error: Input CSV file not found.[/bold red]'
        )