#!/usr/bin/env python3
"""Helper script to split SRT into batches and merge translations back."""
import argparse
import json
import re
import sys
import os
import glob


def parse_srt(filepath):
    """Parse SRT file into list of entries."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    entries = []
    blocks = re.split(r'\n\n+', content.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 2:
            num = lines[0].strip()
            timestamp = lines[1].strip()
            text = '\n'.join(lines[2:])
            entries.append({
                'num': num,
                'timestamp': timestamp,
                'text': text
            })
    return entries


def strip_trailing_period(entries):
    """Remove trailing '。' from text fields."""
    count = 0
    for entry in entries:
        if entry['text'].endswith('。'):
            entry['text'] = entry['text'][:-1]
            count += 1
    return count


def split_into_batches(entries, batch_size, output_dir):
    """Split entries into batch JSON files."""
    os.makedirs(output_dir, exist_ok=True)
    batch_num = 0
    for i in range(0, len(entries), batch_size):
        batch = entries[i:i+batch_size]
        batch_file = os.path.join(output_dir, f'batch_{batch_num:03d}.json')
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)
        batch_num += 1
        print(f'  {batch_file} ({len(batch)} entries)')
    return batch_num


def merge_translations(batch_dir, output_srt):
    """Merge translated batch JSON files into final SRT."""
    batch_files = sorted([f for f in os.listdir(batch_dir)
                          if f.startswith('translated_') and f.endswith('.json')])
    source_files = sorted([f for f in os.listdir(batch_dir)
                           if f.startswith('batch_') and f.endswith('.json')])

    if not batch_files:
        print(f'Error: no translated_*.json files found in {batch_dir}', file=sys.stderr)
        sys.exit(1)

    # Check completeness
    expected = {f.replace('batch_', 'translated_') for f in source_files}
    actual = set(batch_files)
    missing = sorted(expected - actual)
    if missing:
        print(f'Warning: {len(missing)} batch(es) not yet translated:', file=sys.stderr)
        for m in missing:
            print(f'  {m}', file=sys.stderr)
        print('Proceeding with available translations...', file=sys.stderr)

    all_entries = []
    for bf in batch_files:
        filepath = os.path.join(batch_dir, bf)
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = json.load(f)
            all_entries.extend(entries)

    with open(output_srt, 'w', encoding='utf-8') as f:
        for entry in all_entries:
            f.write(f"{entry['num']}\n")
            f.write(f"{entry['timestamp']}\n")
            f.write(f"{entry['text']}\n")
            f.write('\n')

    print(f'Wrote {output_srt} with {len(all_entries)} entries')


def validate_translations(batch_dir):
    """Validate translated batches against source batches."""
    source_files = sorted([f for f in os.listdir(batch_dir)
                           if f.startswith('batch_') and f.endswith('.json')])
    translated_files = sorted([f for f in os.listdir(batch_dir)
                               if f.startswith('translated_') and f.endswith('.json')])

    if not source_files:
        print(f'Error: no batch_*.json files found in {batch_dir}', file=sys.stderr)
        sys.exit(1)

    expected = {f.replace('batch_', 'translated_') for f in source_files}
    actual = set(translated_files)
    missing = sorted(expected - actual)
    errors = 0

    # 1. Check completeness
    print(f'[Completeness] {len(actual)}/{len(expected)} batches translated')
    if missing:
        errors += len(missing)
        for m in missing:
            print(f'  MISSING: {m}')

    # 2. Check each translated batch
    for tf in translated_files:
        sf = tf.replace('translated_', 'batch_')
        if sf not in [f for f in source_files]:
            continue

        src_path = os.path.join(batch_dir, sf)
        tr_path = os.path.join(batch_dir, tf)

        with open(src_path, 'r', encoding='utf-8') as f:
            src_entries = json.load(f)
        with open(tr_path, 'r', encoding='utf-8') as f:
            tr_entries = json.load(f)

        label = tf

        # Check entry count
        if len(src_entries) != len(tr_entries):
            print(f'  [{label}] Entry count mismatch: source={len(src_entries)}, translated={len(tr_entries)}')
            errors += 1
            continue

        # Check num and timestamp integrity
        for i, (s, t) in enumerate(zip(src_entries, tr_entries)):
            if s['num'] != t['num']:
                print(f'  [{label}] Entry {i}: num changed "{s["num"]}" -> "{t["num"]}"')
                errors += 1
            if s['timestamp'] != t['timestamp']:
                print(f'  [{label}] Entry {i}: timestamp changed "{s["timestamp"]}" -> "{t["timestamp"]}"')
                errors += 1
            if s['text'] == t['text']:
                print(f'  [{label}] Entry {i}: text unchanged (possibly not translated): "{s["text"][:50]}"')

    if errors == 0:
        print('All checks passed.')
    else:
        print(f'\n{errors} error(s) found.', file=sys.stderr)
        sys.exit(1)


def clean_batches(batch_dir):
    """Remove all batch and translated JSON files."""
    patterns = ['batch_*.json', 'translated_*.json']
    total = 0
    for pattern in patterns:
        files = glob.glob(os.path.join(batch_dir, pattern))
        for f in files:
            os.remove(f)
            total += 1
    print(f'Removed {total} files from {batch_dir}')


def main():
    parser = argparse.ArgumentParser(
        description='SRT subtitle batch translation helper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  %(prog)s split input.srt batches/
  %(prog)s split input.srt batches/ -n 200
  %(prog)s merge batches/ output.srt
  %(prog)s validate batches/
  %(prog)s clean batches/"""
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # split
    p_split = sub.add_parser('split', help='Split SRT file into JSON batches')
    p_split.add_argument('srt_file', help='Input SRT file')
    p_split.add_argument('output_dir', help='Output directory for batch files')
    p_split.add_argument('-n', '--batch-size', type=int, default=350,
                         help='Entries per batch (default: 350)')
    p_split.add_argument('--no-strip-period', action='store_true',
                         help='Do NOT remove trailing 。 from subtitle text')

    # merge
    p_merge = sub.add_parser('merge', help='Merge translated JSON batches into SRT')
    p_merge.add_argument('batch_dir', help='Directory containing translated_*.json')
    p_merge.add_argument('output_srt', help='Output SRT file path')

    # validate
    p_validate = sub.add_parser('validate', help='Validate translations against source batches')
    p_validate.add_argument('batch_dir', help='Directory containing batch and translated files')

    # clean
    p_clean = sub.add_parser('clean', help='Remove all batch/translated JSON files')
    p_clean.add_argument('batch_dir', help='Directory to clean')

    args = parser.parse_args()

    if args.command == 'split':
        entries = parse_srt(args.srt_file)
        print(f'Parsed {len(entries)} entries from {args.srt_file}')
        if not args.no_strip_period:
            count = strip_trailing_period(entries)
            print(f'Stripped trailing 。 from {count} entries')
        n = split_into_batches(entries, args.batch_size, args.output_dir)
        print(f'Created {n} batches ({args.batch_size} entries each) in {args.output_dir}')

    elif args.command == 'merge':
        merge_translations(args.batch_dir, args.output_srt)

    elif args.command == 'validate':
        validate_translations(args.batch_dir)

    elif args.command == 'clean':
        clean_batches(args.batch_dir)


if __name__ == '__main__':
    main()
