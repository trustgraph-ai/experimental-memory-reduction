#!/usr/bin/env python3
"""
Remove monitoring stack (Grafana, Prometheus, Loki) from docker-compose.yaml.
Edits the file in place.

Usage: ./remove-monitoring.py docker-compose.yaml
"""

import sys
import argparse
from ruamel.yaml import YAML

# Services to remove
MONITORING_SERVICES = ['grafana', 'prometheus', 'loki']

# Volumes to remove (associated with monitoring)
MONITORING_VOLUMES = ['grafana-storage', 'prometheus-data', 'loki-data']


def main():
    parser = argparse.ArgumentParser(
        description='Remove monitoring stack (Grafana, Prometheus, Loki) from docker-compose.yaml'
    )
    parser.add_argument('compose_file', help='Path to docker-compose.yaml')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show changes without modifying file')
    parser.add_argument('--keep-volumes', action='store_true',
                        help='Keep volume definitions (only remove services)')
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
    removed_services = []
    removed_volumes = []

    # Remove monitoring services
    for service_name in MONITORING_SERVICES:
        if service_name in services:
            if not args.dry_run:
                del services[service_name]
            removed_services.append(service_name)
            print(f"Removing service: {service_name}")
        else:
            print(f"Service '{service_name}' not found (skipping)")

    # Remove associated volumes
    if not args.keep_volumes and 'volumes' in data:
        volumes = data['volumes']
        for volume_name in MONITORING_VOLUMES:
            if volume_name in volumes:
                if not args.dry_run:
                    del volumes[volume_name]
                removed_volumes.append(volume_name)
                print(f"Removing volume: {volume_name}")

    if args.dry_run:
        print("\n=== DRY RUN - No changes written ===")
    else:
        with open(args.compose_file, 'w') as f:
            yaml.dump(data, f)
        print(f"\nUpdated {args.compose_file}")

    # Summary
    print("\n=== Summary ===")
    print(f"Services removed: {', '.join(removed_services) if removed_services else 'none'}")
    print(f"Volumes removed: {', '.join(removed_volumes) if removed_volumes else 'none'}")

    # Memory savings estimate
    memory_saved = 0
    if 'grafana' in removed_services:
        memory_saved += 256
    if 'prometheus' in removed_services:
        memory_saved += 128
    if 'loki' in removed_services:
        memory_saved += 256

    print(f"\nEstimated memory savings: ~{memory_saved}M")


if __name__ == '__main__':
    main()
