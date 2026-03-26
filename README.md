# Wasabi Restic Backup Script

This script automates backups to a [Wasabi](https://wasabi.com/) S3-compatible bucket using [restic](https://restic.net/).
It loads secrets from `.env.local`, builds a restic repository string, and runs `restic backup` with redacted environment logging.

## Features

- Two subcommands: `init` (initialize a new repository) and `backup` (run a backup).
- Backup a single source path with `-s/--source`.
- Backup multiple source paths from a JSON config file with `-f/--file`.
- Load secrets from `.env.local` via [python-dotenv](https://pypi.org/project/python-dotenv/).
- Support a prebuilt restic repository via `--repository` or `RESTIC_REPOSITORY`.
- Redact sensitive environment values in output.
- Support dry-run mode for command verification.

## Requirements

- Python 3.8+
- [restic](https://restic.net/) installed and available on `PATH`
- Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

The script loads `.env.local` automatically and uses these variables:

| Variable | Required | Description |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | Yes | Wasabi access key |
| `AWS_SECRET_ACCESS_KEY` | Yes | Wasabi secret key |
| `RESTIC_PASSWORD` | Yes | Restic repository encryption password |
| `WASABI_ENDPOINT` | No | S3 endpoint (defaults to `s3.<region>.wasabisys.com`) |
| `WASABI_REGION` | No | Wasabi region, e.g. `us-east-2` (used to derive endpoint) |
| `WASABI_BUCKET` | No | Bucket name (used when `RESTIC_REPOSITORY` is not set) |
| `RESTIC_REPOSITORY` | No | Full restic repository string (overrides bucket/prefix/region) |
| `RESTIC_PREFIX` | No | Prefix (folder) inside bucket |
| `FILE_PATH_CONFIG_PATH` | No | Path to JSON config file (backup subcommand only) |

Only `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `RESTIC_PASSWORD`, and `WASABI_ENDPOINT` are passed to the restic subprocess. The script builds a minimal environment to avoid leaking unrelated variables.

Create a `RESTIC_PASSWORD` via `openssl rand -base64 32` for best security.

## Subcommands

### `init` — Initialize a New Repository

```bash
python travel-backup-script.py init --bucket my-bucket --region us-east-2 --dry-run
```

### `backup` — Run a Backup

```bash
python travel-backup-script.py backup --source /etc --bucket my-bucket --dry-run
```

## Repository Resolution

The repository string is resolved in this order:

1. `--repository` CLI flag or `RESTIC_REPOSITORY` env var (must match `s3:s3.<region>.wasabisys.com/<bucket>[/<prefix>]`).
2. Otherwise, built from `--bucket` / `WASABI_BUCKET`, `--region` / `WASABI_REGION`, `WASABI_ENDPOINT`, and `--prefix` / `RESTIC_PREFIX`.

## CLI Options

Shared options (both `init` and `backup`):

- `--bucket`: Wasabi bucket name (or set `WASABI_BUCKET`)
- `--prefix`: Prefix inside the bucket (or set `RESTIC_PREFIX`)
- `--region`: Wasabi region, e.g. `us-east-2` (or set `WASABI_REGION`)
- `--repository`: Full restic repository string (or set `RESTIC_REPOSITORY`)
- `--dry-run`: Print the command and redacted environment without running `restic`

Backup-only options:

- `-s`, `--source`: Single file or directory to back up
- `-f`, `--file`: Path to a JSON file containing `{"paths": ["..."]}`

`-s/--source` and `-f/--file` are mutually exclusive. One of them (or the `FILE_PATH_CONFIG_PATH` env var) is required for backup.

## JSON File Format

Example config:

```json
{
  "paths": [
    "/path/to/Documents",
    "/path/to/Pictures"
  ]
}
```

## Examples

Initialize a repository (dry run):

```bash
python travel-backup-script.py init --bucket my-bucket --region us-east-2 --dry-run
```

Backup a single source (dry run):

```bash
python travel-backup-script.py backup --source /etc --bucket my-bucket --dry-run
```

Backup from a JSON file (dry run):

```bash
python travel-backup-script.py backup --file backup-paths.json --bucket my-bucket --dry-run
```

Use a custom prefix:

```bash
python travel-backup-script.py backup --source ~/Documents --bucket my-bucket --prefix laptop-backups
```

Use a full repository string:

```bash
python travel-backup-script.py backup --source ~/Documents --repository s3:s3.us-east-2.wasabisys.com/my-bucket/laptop-backups
```
