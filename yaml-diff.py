#!/usr/bin/env python3
"""
Compare two YAML files and show differences.
Useful for comparing docker-compose.yaml before/after modifications.

Usage: ./yaml-diff.py original.yaml modified.yaml
"""

import sys
import argparse
from ruamel.yaml import YAML
from typing import Any


def flatten_dict(d: dict, parent_key: str = '', sep: str = '.') -> dict:
    """Flatten a nested dictionary into dot-notation keys."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # For lists, show as single value or flatten if contains dicts
            if v and isinstance(v[0], dict):
                for i, item in enumerate(v):
                    items.extend(flatten_dict(item, f"{new_key}[{i}]", sep=sep).items())
            else:
                items.append((new_key, v))
        else:
            items.append((new_key, v))
    return dict(items)


def format_value(v: Any) -> str:
    """Format a value for display."""
    if isinstance(v, list):
        if len(v) <= 3:
            return str(v)
        return f"[{v[0]}, {v[1]}, ... ({len(v)} items)]"
    if isinstance(v, str) and len(v) > 60:
        return f"{v[:57]}..."
    return str(v)


def compare_yaml(file1: str, file2: str, context: str = None):
    """Compare two YAML files and print differences."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096

    with open(file1, 'r') as f:
        data1 = yaml.load(f)
    with open(file2, 'r') as f:
        data2 = yaml.load(f)

    # Optionally focus on a specific section
    if context:
        parts = context.split('.')
        for part in parts:
            if data1 and part in data1:
                data1 = data1[part]
            else:
                data1 = {}
            if data2 and part in data2:
                data2 = data2[part]
            else:
                data2 = {}

    flat1 = flatten_dict(data1) if data1 else {}
    flat2 = flatten_dict(data2) if data2 else {}

    all_keys = set(flat1.keys()) | set(flat2.keys())

    added = []
    removed = []
    changed = []

    for key in sorted(all_keys):
        in1 = key in flat1
        in2 = key in flat2

        if in1 and not in2:
            removed.append((key, flat1[key]))
        elif in2 and not in1:
            added.append((key, flat2[key]))
        elif flat1[key] != flat2[key]:
            changed.append((key, flat1[key], flat2[key]))

    return added, removed, changed


def print_service_summary(file1: str, file2: str):
    """Print a summary of service-level changes."""
    yaml = YAML()

    with open(file1, 'r') as f:
        data1 = yaml.load(f)
    with open(file2, 'r') as f:
        data2 = yaml.load(f)

    services1 = set(data1.get('services', {}).keys())
    services2 = set(data2.get('services', {}).keys())

    added = services2 - services1
    removed = services1 - services2

    if added or removed:
        print("=== Service Changes ===")
        if added:
            print(f"  Added: {', '.join(sorted(added))}")
        if removed:
            print(f"  Removed: {', '.join(sorted(removed))}")
        print()

    return services1 & services2  # Return common services


def main():
    parser = argparse.ArgumentParser(
        description='Compare two YAML files and show differences'
    )
    parser.add_argument('file1', help='Original YAML file')
    parser.add_argument('file2', help='Modified YAML file')
    parser.add_argument('--section', '-s',
                        help='Focus on specific section (e.g., "services.pulsar")')
    parser.add_argument('--memory-only', '-m', action='store_true',
                        help='Only show memory-related changes')
    parser.add_argument('--services', action='store_true',
                        help='Show per-service comparison')
    args = parser.parse_args()

    print(f"Comparing: {args.file1} -> {args.file2}\n")

    if args.services:
        # Per-service comparison
        common_services = print_service_summary(args.file1, args.file2)

        yaml = YAML()
        with open(args.file1, 'r') as f:
            data1 = yaml.load(f)
        with open(args.file2, 'r') as f:
            data2 = yaml.load(f)

        for service in sorted(common_services):
            svc1 = flatten_dict(data1['services'][service])
            svc2 = flatten_dict(data2['services'][service])

            changes = []
            all_keys = set(svc1.keys()) | set(svc2.keys())

            for key in sorted(all_keys):
                if args.memory_only and 'memory' not in key.lower() and 'mem' not in key.lower():
                    continue

                in1 = key in svc1
                in2 = key in svc2

                if in1 and not in2:
                    changes.append(f"  - {key}: {format_value(svc1[key])}")
                elif in2 and not in1:
                    changes.append(f"  + {key}: {format_value(svc2[key])}")
                elif svc1[key] != svc2[key]:
                    changes.append(f"  ~ {key}:")
                    changes.append(f"      {format_value(svc1[key])} -> {format_value(svc2[key])}")

            if changes:
                print(f"=== {service} ===")
                for c in changes:
                    print(c)
                print()

    else:
        # Full comparison
        added, removed, changed = compare_yaml(args.file1, args.file2, args.section)

        if args.memory_only:
            added = [(k, v) for k, v in added if 'memory' in k.lower() or 'mem' in k.lower()]
            removed = [(k, v) for k, v in removed if 'memory' in k.lower() or 'mem' in k.lower()]
            changed = [(k, o, n) for k, o, n in changed if 'memory' in k.lower() or 'mem' in k.lower()]

        if removed:
            print("=== Removed ===")
            for key, val in removed:
                print(f"  - {key}: {format_value(val)}")
            print()

        if added:
            print("=== Added ===")
            for key, val in added:
                print(f"  + {key}: {format_value(val)}")
            print()

        if changed:
            print("=== Changed ===")
            for key, old, new in changed:
                print(f"  ~ {key}:")
                print(f"      {format_value(old)} -> {format_value(new)}")
            print()

        if not (added or removed or changed):
            print("No differences found.")

    # Summary
    total_changes = len(added) + len(removed) + len(changed) if not args.services else 0
    if total_changes:
        print(f"Total: {len(added)} added, {len(removed)} removed, {len(changed)} changed")


if __name__ == '__main__':
    main()
