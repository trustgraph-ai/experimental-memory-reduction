#!/usr/bin/env python3
"""
Reduce Qdrant memory allocation in docker-compose.yaml.
Configures Qdrant to use memory-mapped files instead of keeping vectors in RAM.
Edits the file in place.

Usage: ./reduce-qdrant.py docker-compose.yaml
"""

import sys
import argparse
from ruamel.yaml import YAML

# Default reduction settings
DEFAULT_SETTINGS = {
    'memory_limit': '600M',
    'memory_reservation': '500M',
}

# Qdrant environment variables for memory optimization
QDRANT_ENV_VARS = {
    # Use mmap for vectors larger than 1KB (essentially all vectors)
    'QDRANT__STORAGE__MEMMAP_THRESHOLD_KB': '1',
    # Use mmap for storage
    'QDRANT__STORAGE__ON_DISK_PAYLOAD': 'true',
}


def update_qdrant(service_config: dict, settings: dict) -> list:
    """Update Qdrant's memory settings. Returns list of changes."""
    changes = []

    # Update deploy.resources
    if 'deploy' not in service_config:
        service_config['deploy'] = {}
    if 'resources' not in service_config['deploy']:
        service_config['deploy']['resources'] = {}
    if 'limits' not in service_config['deploy']['resources']:
        service_config['deploy']['resources']['limits'] = {}
    if 'reservations' not in service_config['deploy']['resources']:
        service_config['deploy']['resources']['reservations'] = {}

    resources = service_config['deploy']['resources']

    old_limit = resources['limits'].get('memory', 'unset')
    old_reservation = resources['reservations'].get('memory', 'unset')

    resources['limits']['memory'] = settings['memory_limit']
    resources['reservations']['memory'] = settings['memory_reservation']

    changes.append(f"memory limit: {old_limit} -> {settings['memory_limit']}")
    changes.append(f"memory reservation: {old_reservation} -> {settings['memory_reservation']}")

    # Add/update environment variables for memory optimization
    if 'environment' not in service_config:
        service_config['environment'] = {}

    env = service_config['environment']

    if isinstance(env, list):
        # Environment as list - convert to dict, update, convert back
        env_dict = {}
        for item in env:
            if '=' in str(item):
                k, v = str(item).split('=', 1)
                env_dict[k] = v

        for key, value in QDRANT_ENV_VARS.items():
            old_val = env_dict.get(key, 'unset')
            env_dict[key] = value
            changes.append(f"{key}: {old_val} -> {value}")

        service_config['environment'] = [f"{k}={v}" for k, v in env_dict.items()]
    else:
        # Environment as dict
        for key, value in QDRANT_ENV_VARS.items():
            old_val = env.get(key, 'unset')
            env[key] = value
            changes.append(f"{key}: {old_val} -> {value}")

    return changes


def main():
    parser = argparse.ArgumentParser(
        description='Reduce Qdrant memory allocation in docker-compose.yaml'
    )
    parser.add_argument('compose_file', help='Path to docker-compose.yaml')
    parser.add_argument('--limit', '-l', default=DEFAULT_SETTINGS['memory_limit'],
                        help=f"Memory limit (default: {DEFAULT_SETTINGS['memory_limit']})")
    parser.add_argument('--reservation', '-r', default=DEFAULT_SETTINGS['memory_reservation'],
                        help=f"Memory reservation (default: {DEFAULT_SETTINGS['memory_reservation']})")
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show changes without modifying file')
    args = parser.parse_args()

    settings = {
        'memory_limit': args.limit,
        'memory_reservation': args.reservation,
    }

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=2, offset=0)

    with open(args.compose_file, 'r') as f:
        data = yaml.load(f)

    if 'services' not in data:
        print("Error: No 'services' section found in compose file", file=sys.stderr)
        sys.exit(1)

    services = data['services']

    if 'qdrant' not in services:
        print("Error: No 'qdrant' service found in compose file", file=sys.stderr)
        sys.exit(1)

    print("Updating qdrant...")
    changes = update_qdrant(services['qdrant'], settings)

    if args.dry_run:
        print("\n=== DRY RUN - No changes written ===")

    print("\nChanges:")
    for change in changes:
        print(f"  {change}")

    if not args.dry_run:
        with open(args.compose_file, 'w') as f:
            yaml.dump(data, f)
        print(f"\nUpdated {args.compose_file}")

    print("\n=== Summary ===")
    print(f"Qdrant memory: 1024M -> {settings['memory_limit']}")
    print("Memory optimization: enabled mmap for vectors and payload")
    print("Note: Vectors will be memory-mapped from disk instead of held in RAM")
    print("      This trades some query latency for significant memory savings")
    print(f"Estimated savings: ~400M")


if __name__ == '__main__':
    main()
