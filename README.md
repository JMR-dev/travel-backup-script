# Wasabi Restic Backup Script

This script automates backups to a [Wasabi](https://wasabi.com/) (S3-compatible) bucket using [restic](https://restic.net/).  
It supports environment-based secrets (via `.env` + [python-dotenv](https://pypi.org/project/python-dotenv/)), CLI overrides, and dry-run/verbose modes.

---

## Features

- Backup any file or directory to Wasabi S3 storage with restic.
- Secrets loaded from a `.env` file (no need to type passwords on the CLI).
- CLI arguments override `.env` and system environment variables.
- Verbose and dry-run modes for debugging.
- Environment variable redaction in output (so logs won’t leak secrets).

---

## Requirements

- Python 3.8+
- [restic](https://restic.net/) installed and in your `PATH`
- `python-dotenv` installed:
  ```bash
  pip install python-dotenv


## Initialize the Repository (first run only)

restic -r s3:s3.[REGION].wasabisys.com/[BUCKET_NAME]/[PREFIX] init


## CLI Options

Option	Description
--source, -s	Source path to back up (required)
--bucket, -b	Wasabi bucket name (required unless --repository used)
--endpoint, -e	S3 endpoint (default: s3.wasabisys.com or from env)
--prefix, -p	Path inside bucket (default: travel-backup)
--access-key	Wasabi access key (overrides env/.env)
--secret-key	Wasabi secret key (overrides env/.env)
--password, -P	Restic password (overrides env/.env)
--repository, -r	Full restic repository string (overrides bucket/endpoint/prefix)
--env-file	Path to .env file (default: .env)
--dry-run	Show command and env but do not execute
--verbose	Show extra debug info

## Example Dry Run
python travel-backup-backup.py --source /etc --bucket my-bucket --dry-run --verbose


## Run the Backup

python backup.py --source /path/to/data --bucket my-bucket

**Example with overrides:**
python backup.py \
  --source ~/Documents \
  --bucket my-bucket \
  --prefix laptop-backups \
  --verbose

