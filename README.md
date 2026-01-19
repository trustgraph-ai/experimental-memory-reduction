# TrustGraph Memory Reduction Scripts

Scripts to reduce memory usage in TrustGraph docker-compose deployments.

## Prerequisites

```bash
pip install ruamel.yaml
```

## Scripts

### reduce-pulsar-memory.py

Reduces memory allocation for the Apache Pulsar stack (zookeeper, bookie, pulsar, pulsar-init).

```bash
./reduce-pulsar-memory.py docker-compose.yaml
./reduce-pulsar-memory.py docker-compose.yaml --dry-run  # Preview changes
```

**Changes:**
| Service | Before | After |
|---------|--------|-------|
| zookeeper | 512M | 300M |
| bookie | 1024M | 600M |
| pulsar | 800M | 512M |
| pulsar-init | 256M | 128M |

**Estimated savings:** ~1 GB

---

### reduce-cassandra.py

Reduces Cassandra memory allocation and JVM heap size.

```bash
./reduce-cassandra.py docker-compose.yaml
./reduce-cassandra.py docker-compose.yaml --heap 150M --limit 500M  # Custom values
```

**Options:**
- `--limit`, `-l`: Memory limit (default: 600M)
- `--reservation`, `-r`: Memory reservation (default: 500M)
- `--heap`: JVM heap size (default: 200M)

**Estimated savings:** ~400M

---

### reduce-qdrant.py

Reduces Qdrant memory allocation and enables memory-mapped storage.

```bash
./reduce-qdrant.py docker-compose.yaml
```

**Options:**
- `--limit`, `-l`: Memory limit (default: 600M)
- `--reservation`, `-r`: Memory reservation (default: 500M)

**Note:** Enables mmap for vectors and payloads, trading some query latency for memory savings.

**Estimated savings:** ~400M

---

### reduce-reservations.py

Reduces memory reservations by 50% across ALL services while keeping limits unchanged. This allows memory overcommit - services can still burst to their limit, but the system doesn't need to guarantee the full amount upfront.

```bash
./reduce-reservations.py docker-compose.yaml
./reduce-reservations.py docker-compose.yaml --factor 0.25  # Reduce to 25%
```

**Options:**
- `--factor`, `-f`: Reduction factor (default: 0.5 = 50%)
- `--min-memory`, `-m`: Minimum reservation in MB (default: 32)

**Estimated savings:** Depends on current allocations, typically 3-5 GB

---

### remove-monitoring.py

Removes the monitoring stack (Grafana, Prometheus, Loki) and associated volumes.

```bash
./remove-monitoring.py docker-compose.yaml
./remove-monitoring.py docker-compose.yaml --keep-volumes  # Only remove services
```

**Estimated savings:** ~640M

---

### yaml-diff.py

Compare two YAML files to see what changed. Useful for reviewing changes before/after running scripts.

```bash
./yaml-diff.py original.yaml modified.yaml
./yaml-diff.py original.yaml modified.yaml --services        # Per-service comparison
./yaml-diff.py original.yaml modified.yaml --memory-only     # Only memory changes
./yaml-diff.py original.yaml modified.yaml -s services.pulsar  # Specific section
```

## Recommended Order

For maximum memory reduction with minimal risk:

1. **Start with a backup:**
   ```bash
   cp docker-compose.yaml docker-compose.yaml.backup
   ```

2. **Reduce reservations (safe, allows overcommit):**
   ```bash
   ./reduce-reservations.py docker-compose.yaml
   ```

3. **Reduce Pulsar stack:**
   ```bash
   ./reduce-pulsar-memory.py docker-compose.yaml
   ```

4. **Reduce databases:**
   ```bash
   ./reduce-cassandra.py docker-compose.yaml
   ./reduce-qdrant.py docker-compose.yaml
   ```

5. **Optional - remove monitoring:**
   ```bash
   ./remove-monitoring.py docker-compose.yaml
   ```

6. **Review changes:**
   ```bash
   ./yaml-diff.py docker-compose.yaml.backup docker-compose.yaml --memory-only
   ```

## Expected Results

| Stage | Cumulative Memory |
|-------|-------------------|
| Original | ~11-12 GB |
| After reduce-reservations | ~9-10 GB (limits unchanged) |
| After reduce-pulsar-memory | ~8-9 GB |
| After reduce-cassandra | ~7.5-8.5 GB |
| After reduce-qdrant | ~7-8 GB |
| After remove-monitoring | ~6.5-7.5 GB |

**Note:** These are memory *limits*. Actual usage will be lower, especially after reducing reservations.

## Risks

- **Pulsar stack:** Aggressive tuning may cause instability under heavy load. Monitor for OOM errors.
- **Cassandra:** Reduced heap may cause GC pauses. Monitor with `nodetool`.
- **Qdrant:** Memory-mapped storage trades RAM for disk I/O. May increase query latency.
- **Reservations:** Over-committing memory works until multiple services spike simultaneously.

## Reverting Changes

```bash
cp docker-compose.yaml.backup docker-compose.yaml
```
