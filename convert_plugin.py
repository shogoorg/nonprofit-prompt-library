import argparse
import glob
import json
import os
import re
import sys
import pandas as pd


DEFAULT_LABELS = {
    'ja': {
        'task': 'タスク',
        'tool': 'ツール',
        'prompt': 'プロンプト',
        'impact': 'インパクト',
    },
    'en': {
        'task': 'Task',
        'tool': 'Tool',
        'prompt': 'Prompt',
        'impact': 'Impact',
    }
}



def load_mapping(mapping_filepath):
    """Load external mapping configuration file"""
    if os.path.exists(mapping_filepath):
        with open(mapping_filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
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
    category_raw = mapping.get('categories', {})
    category_map = {val: key for key, val in category_raw.items()}
    task_raw = mapping.get('tasks', {})
    task_map = {val: key for key, val in task_raw.items()}

    lang_defaults = DEFAULT_LABELS.get(lang_code, DEFAULT_LABELS['en'])
    labels = {
        key: mapping.get('labels', {}).get(key, val)
        for key, val in lang_defaults.items()
    }

    task_label = labels['task']
    tool_label = labels['tool']
    prompt_label = labels['prompt']
    impact_label = labels['impact']

    skills_root = os.path.join(output_dir, 'skills', lang_code)
    os.makedirs(skills_root, exist_ok=True)

    # Read CSV with pandas and automatically clean BOM/whitespace
    try:
        df = pd.read_csv(csv_file_path, encoding='utf-8-sig').fillna('')
        df.columns = [
            str(col).strip().replace('\ufeff', '') for col in df.columns
        ]
    except Exception as e:
        print(f'Error: Failed to read CSV file: {e}', file=sys.stderr)
        sys.exit(1)

    required_keys = ['category', 'task', 'tool', 'prompt', 'impact']
    col_mapping = mapping.get('columns', {})
    detected_cols = {}

    for key in required_keys:
        kws = col_mapping.get(key)
        if not kws:
            print(f'Error: Column mapping configuration for "{key}" is missing in JSON.', file=sys.stderr)
            sys.exit(1)

        kws = [str(k).lower() for k in kws]
        matched = None
        for col in df.columns:
            if any(kw in str(col).lower() for kw in kws):
                matched = col
                break

        if not matched:
            print(
                f'Error: Required column for "{key}" (keywords: {kws}) not found in CSV.',
                file=sys.stderr
            )
            sys.exit(1)

        detected_cols[key] = matched

    category_data = {}

    for _, row in df.iterrows():
        category = str(row.get(detected_cols['category'], '')).strip() or 'Other'
        task = str(row.get(detected_cols['task'], '')).strip() or 'Task'
        tool = str(row.get(detected_cols['tool'], '')).strip() or 'Unspecified'
        prompt = str(row.get(detected_cols['prompt'], '')).strip()
        impact = str(row.get(detected_cols['impact'], '')).strip()

        if not prompt:
            continue

        if category not in category_data:
            category_data[category] = []

        category_data[category].append(
            {
                'task': task,
                'tool': tool,
                'prompt': prompt,
                'impact': impact,
            }
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

        for item in items:
            task_name = item['task']
            task_slug = task_map.get(task_name, sanitize_slug(task_name))

            task_slug_counters[task_slug] = (
                task_slug_counters.get(task_slug, 0) + 1
            )
            sub_seq = task_slug_counters[task_slug]

            ref_filename = f'{task_slug}-{sub_seq:02d}.md'
            ref_filepath = os.path.join(ref_dir, ref_filename)

            ref_content = f"""# {task_label}: {task_name} {sub_seq}

## {task_label}
{task_name}
"""
            if item['tool'] and item['tool'] != 'Unspecified':
                ref_content += f"""
## {tool_label}
{item['tool']}
"""

            ref_content += f"""
## {prompt_label}

{item['prompt']}
"""

            if item['impact']:
                ref_content += f"""
## {impact_label}
{item['impact']}
"""

            # Clean up multiple newlines at the end
            ref_content = ref_content.strip() + '\n'

            with open(ref_filepath, 'w', encoding='utf-8') as rf:
                rf.write(ref_content)

            index_list.append(
                f"- **{task_name} {sub_seq}** (`references/{ref_filename}`)"
            )

        skill_md_path = os.path.join(cat_dir, 'SKILL.md')
        
        skill_md_content = f"""---
name: {category_name}
description: {category_name}
---

# {category_name}

""" + '\n'.join(
            index_list
        ) + '\n'

        with open(skill_md_path, 'w', encoding='utf-8') as sf:
            sf.write(skill_md_content)



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
        print('Error: Input CSV file not found.', file=sys.stderr)