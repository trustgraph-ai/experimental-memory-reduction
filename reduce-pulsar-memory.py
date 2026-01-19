#!/usr/bin/env python3
"""
Reduce memory allocation for the Pulsar stack (zookeeper, bookie, pulsar, pulsar-init).
Edits a docker-compose.yaml file in place.

Usage: ./reduce-pulsar-memory.py docker-compose.yaml
"""

import sys
import argparse
from ruamel.yaml import YAML

# Memory reduction targets
PULSAR_STACK_SETTINGS = {
    'zookeeper': {
        'memory_limit': '300M',
        'memory_reservation': '200M',
        'jvm_env_var': 'PULSAR_MEM',
        'jvm_settings': '-Xms128m -Xmx128m -XX:MaxDirectMemorySize=64m',
    },
    'bookie': {
        'memory_limit': '600M',
        'memory_reservation': '400M',
        'jvm_env_var': 'BOOKIE_MEM',
        'jvm_settings': '-Xms128m -Xmx128m -XX:MaxDirectMemorySize=128m',
    },
    'pulsar': {
        'memory_limit': '512M',
        'memory_reservation': '400M',
        'jvm_env_var': 'PULSAR_MEM',
        'jvm_settings': '-Xms192m -Xmx192m -XX:MaxDirectMemorySize=192m',
    },
    'pulsar-init': {
        'memory_limit': '128M',
        'memory_reservation': '128M',
        'jvm_env_var': 'PULSAR_MEM',
        'jvm_settings': '-Xms64m -Xmx64m -XX:MaxDirectMemorySize=64m',
    },
}


def update_service(service_name, service_config, settings):
    """Update a service's memory settings."""
    changes = []

    # Update deploy.resources.limits.memory
    if 'deploy' not in service_config:
        service_config['deploy'] = {}
    if 'resources' not in service_config['deploy']:
        service_config['deploy']['resources'] = {}
    if 'limits' not in service_config['deploy']['resources']:
        service_config['deploy']['resources']['limits'] = {}
    if 'reservations' not in service_config['deploy']['resources']:
        service_config['deploy']['resources']['reservations'] = {}

    old_limit = service_config['deploy']['resources']['limits'].get('memory', 'unset')
    old_reservation = service_config['deploy']['resources']['reservations'].get('memory', 'unset')

    service_config['deploy']['resources']['limits']['memory'] = settings['memory_limit']
    service_config['deploy']['resources']['reservations']['memory'] = settings['memory_reservation']

    changes.append(f"  memory limit: {old_limit} -> {settings['memory_limit']}")
    changes.append(f"  memory reservation: {old_reservation} -> {settings['memory_reservation']}")

    # Update JVM environment variable
    if 'environment' not in service_config:
        service_config['environment'] = {}

    env = service_config['environment']
    jvm_var = settings['jvm_env_var']

    # Handle environment as list or dict
    if isinstance(env, list):
        # Convert list to dict for easier manipulation
        env_dict = {}
        for item in env:
            if '=' in item:
                k, v = item.split('=', 1)
                env_dict[k] = v
        old_jvm = env_dict.get(jvm_var, 'unset')
        env_dict[jvm_var] = settings['jvm_settings']
        # Convert back to list
        service_config['environment'] = [f"{k}={v}" for k, v in env_dict.items()]
    else:
        old_jvm = env.get(jvm_var, 'unset')
        env[jvm_var] = settings['jvm_settings']

    changes.append(f"  {jvm_var}: {old_jvm} -> {settings['jvm_settings']}")

    return changes


def main():
    parser = argparse.ArgumentParser(
        description='Reduce Pulsar stack memory allocation in docker-compose.yaml'
    )
    parser.add_argument('compose_file', help='Path to docker-compose.yaml')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show changes without modifying file')
    args = parser.parse_args()

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096  # Prevent line wrapping
    yaml.indent(mapping=2, sequence=2, offset=0)  # offset=0 keeps list items aligned with key

    with open(args.compose_file, 'r') as f:
        data = yaml.load(f)

    if 'services' not in data:
        print("Error: No 'services' section found in compose file", file=sys.stderr)
        sys.exit(1)

    services = data['services']
    all_changes = []

    for service_name, settings in PULSAR_STACK_SETTINGS.items():
        if service_name in services:
            print(f"Updating {service_name}...")
            changes = update_service(service_name, services[service_name], settings)
            all_changes.extend([f"{service_name}:"] + changes)
        else:
            print(f"Warning: Service '{service_name}' not found in compose file", file=sys.stderr)

    if args.dry_run:
        print("\n=== DRY RUN - No changes written ===")
        print("\nChanges that would be made:")
        for change in all_changes:
            print(change)
    else:
        with open(args.compose_file, 'w') as f:
            yaml.dump(data, f)
        print(f"\nUpdated {args.compose_file}")
        print("\nChanges made:")
        for change in all_changes:
            print(change)

    # Summary
    print("\n=== Memory Summary ===")
    print("Service        Before    After")
    print("-" * 35)
    print("zookeeper      512M   -> 300M")
    print("bookie         1024M  -> 600M")
    print("pulsar         800M   -> 512M")
    print("pulsar-init    256M   -> 128M")
    print("-" * 35)
    print("Total          2592M  -> 1540M")
    print("Savings:       ~1 GB")


if __name__ == '__main__':
    main()
