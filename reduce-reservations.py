#!/usr/bin/env python3
"""
Reduce memory reservations by 50% across all services.
Keeps limits unchanged, only reduces the guaranteed/reserved memory.

This allows memory overcommit - services can still burst to their limit,
but the system doesn't need to guarantee the full amount upfront.

Usage: ./reduce-reservations.py docker-compose.yaml
"""

import sys
import argparse
import re
from ruamel.yaml import YAML


def parse_memory(mem_str: str) -> int:
    """Parse memory string like '128M' or '1024M' to megabytes."""
    if isinstance(mem_str, int):
        return mem_str
    mem_str = str(mem_str).strip().upper()
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?)B?$', mem_str)
    if not match:
        raise ValueError(f"Cannot parse memory value: {mem_str}")

    value = float(match.group(1))
    unit = match.group(2)

    multipliers = {'': 1, 'K': 1/1024, 'M': 1, 'G': 1024, 'T': 1024*1024}
    return int(value * multipliers.get(unit, 1))


def format_memory(mb: int) -> str:
    """Format megabytes back to string like '128M'."""
    return f"{mb}M"


def reduce_service_reservation(service_name: str, service_config: dict, factor: float) -> dict | None:
    """Reduce a service's memory reservation by the given factor. Returns change info or None."""
    try:
        resources = service_config.get('deploy', {}).get('resources', {})
        reservations = resources.get('reservations', {})

        if 'memory' not in reservations:
            return None

        old_value = reservations['memory']
        old_mb = parse_memory(old_value)
        new_mb = max(32, int(old_mb * factor))  # Don't go below 32M

        if old_mb == new_mb:
            return None

        reservations['memory'] = format_memory(new_mb)

        return {
            'service': service_name,
            'old': old_value,
            'new': format_memory(new_mb),
            'old_mb': old_mb,
            'new_mb': new_mb,
        }
    except Exception as e:
        print(f"Warning: Could not process {service_name}: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Reduce memory reservations by 50% across all services'
    )
    parser.add_argument('compose_file', help='Path to docker-compose.yaml')
    parser.add_argument('--factor', '-f', type=float, default=0.5,
                        help='Reduction factor (default: 0.5 = 50%%)')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show changes without modifying file')
    parser.add_argument('--min-memory', '-m', type=int, default=32,
                        help='Minimum reservation in MB (default: 32)')
    args = parser.parse_args()

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096  # Prevent line wrapping
    yaml.indent(mapping=2, sequence=2, offset=0)

    with open(args.compose_file, 'r') as f:
        data = yaml.load(f)

    if 'services' not in data:
        print("Error: No 'services' section found in compose file", file=sys.stderr)
        sys.exit(1)

    services = data['services']
    changes = []

    for service_name, service_config in services.items():
        change = reduce_service_reservation(service_name, service_config, args.factor)
        if change:
            changes.append(change)

    if args.dry_run:
        print("=== DRY RUN - No changes written ===\n")

    if not changes:
        print("No memory reservations found to modify.")
        return

    # Print changes
    print(f"{'Service':<30} {'Old':>10} {'New':>10} {'Saved':>10}")
    print("-" * 62)

    total_old = 0
    total_new = 0

    for change in sorted(changes, key=lambda x: x['service']):
        saved = change['old_mb'] - change['new_mb']
        total_old += change['old_mb']
        total_new += change['new_mb']
        print(f"{change['service']:<30} {change['old']:>10} {change['new']:>10} {saved:>9}M")

    print("-" * 62)
    print(f"{'TOTAL':<30} {total_old:>9}M {total_new:>9}M {total_old - total_new:>9}M")

    if not args.dry_run:
        with open(args.compose_file, 'w') as f:
            yaml.dump(data, f)
        print(f"\nUpdated {args.compose_file}")

    print(f"\nReservations reduced by {int((1 - args.factor) * 100)}%")
    print(f"Total reservation savings: {total_old - total_new}M ({(total_old - total_new) / 1024:.1f}G)")


if __name__ == '__main__':
    main()
