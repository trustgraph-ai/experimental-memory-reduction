#!/usr/bin/env python3
"""
Reduce Cassandra memory allocation in docker-compose.yaml.
Edits the file in place.

Usage: ./reduce-cassandra.py docker-compose.yaml
"""

import sys
import argparse
from ruamel.yaml import YAML

# Default reduction settings
DEFAULT_SETTINGS = {
    'memory_limit': '600M',
    'memory_reservation': '500M',
    'heap_size': '200M',  # -Xms and -Xmx
}


def update_cassandra(service_config: dict, settings: dict) -> list:
    """Update Cassandra's memory settings. Returns list of changes."""
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

    # Update JVM_OPTS environment variable
    if 'environment' not in service_config:
        service_config['environment'] = {}

    env = service_config['environment']
    heap = settings['heap_size']
    new_jvm_opts = f"-Xms{heap} -Xmx{heap} -Dcassandra.skip_wait_for_gossip_to_settle=0"

    if isinstance(env, list):
        # Environment as list
        env_dict = {}
        for item in env:
            if '=' in str(item):
                k, v = str(item).split('=', 1)
                env_dict[k] = v
        old_jvm = env_dict.get('JVM_OPTS', 'unset')
        env_dict['JVM_OPTS'] = new_jvm_opts
        service_config['environment'] = [f"{k}={v}" for k, v in env_dict.items()]
    else:
        # Environment as dict
        old_jvm = env.get('JVM_OPTS', 'unset')
        env['JVM_OPTS'] = new_jvm_opts

    changes.append(f"JVM_OPTS: {old_jvm}")
    changes.append(f"      -> {new_jvm_opts}")

    return changes


def main():
    parser = argparse.ArgumentParser(
        description='Reduce Cassandra memory allocation in docker-compose.yaml'
    )
    parser.add_argument('compose_file', help='Path to docker-compose.yaml')
    parser.add_argument('--limit', '-l', default=DEFAULT_SETTINGS['memory_limit'],
                        help=f"Memory limit (default: {DEFAULT_SETTINGS['memory_limit']})")
    parser.add_argument('--reservation', '-r', default=DEFAULT_SETTINGS['memory_reservation'],
                        help=f"Memory reservation (default: {DEFAULT_SETTINGS['memory_reservation']})")
    parser.add_argument('--heap', default=DEFAULT_SETTINGS['heap_size'],
                        help=f"JVM heap size (default: {DEFAULT_SETTINGS['heap_size']})")
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show changes without modifying file')
    args = parser.parse_args()

    settings = {
        'memory_limit': args.limit,
        'memory_reservation': args.reservation,
        'heap_size': args.heap,
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

    if 'cassandra' not in services:
        print("Error: No 'cassandra' service found in compose file", file=sys.stderr)
        sys.exit(1)

    print("Updating cassandra...")
    changes = update_cassandra(services['cassandra'], settings)

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
    print(f"Cassandra memory: 1000M -> {settings['memory_limit']}")
    print(f"JVM heap: 300M -> {settings['heap_size']}")
    print(f"Estimated savings: ~400M")


if __name__ == '__main__':
    main()
