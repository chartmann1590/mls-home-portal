# Operations

## Docker

```bash
docker compose up -d --build
docker compose logs -f mls-home-portal
docker compose logs -f scapling-bridge
```

## Backup Saved Data

```bash
tar -czf runtime-data-backup.tgz runtime-data/
```

## Restore

```bash
tar -xzf runtime-data-backup.tgz
```

## Restart Policy

Both services run with `restart: always` for host reboot recovery.
