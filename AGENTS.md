# AGENTS.md

## Repo Overview

- Purpose: run `restic backup` against a Wasabi S3-compatible repository.
- Main entry point: `travel-backup-script.py`.
- Dependencies are intentionally minimal:
  - Python standard library
  - `python-dotenv`
  - External binary: `restic` must already be installed and available on `PATH`
- There are currently no tests, package metadata files, or CI config in this repo.

## File Map

- `travel-backup-script.py`: single-script CLI implementation.
- `requirements.txt`: Python dependency list (`python-dotenv` only).
- `README.md`: user-facing setup and usage docs.
- `.env.example`: template for environment variables.
- `.gitignore`: ignores `.env.*` files (except `.env.example`).

## Current Script Behavior

The script uses two subcommands: `init` and `backup`.

1. Loads `.env.local` automatically via `load_dotenv(".env.local")`.
2. Parses CLI args into subcommands with shared repo flags and backup-specific source flags.
3. Resolves the repository string:
   - `--repository` / `RESTIC_REPOSITORY` takes priority (validated against `s3:s3.<region>.wasabisys.com/...` format).
   - Otherwise built from `--bucket` / `WASABI_BUCKET`, `--region` / `WASABI_REGION`, `WASABI_ENDPOINT`, and `--prefix` / `RESTIC_PREFIX`.
4. Constructs a minimal subprocess environment for `restic`:
   - `WASABI_ENDPOINT`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `RESTIC_PASSWORD`
   - `PATH`, `HOME` if present
   - `SYSTEMROOT`, `SystemRoot`, `COMSPEC` (Windows-specific, required for DNS resolution and shell access)
5. For `init`: runs `restic init` against the resolved repository.
6. For `backup`: resolves input from `--source`, `--file`, or `FILE_PATH_CONFIG_PATH` env var, then runs `restic backup`.
7. Prints the repo, command, and redacted env status before optionally executing `restic`.

## Known Drift / Things To Watch

- The JSON config file must contain a top-level `paths` key with a non-empty array of non-empty strings.
- `--source` and `--file` are mutually exclusive; one of them or `FILE_PATH_CONFIG_PATH` is required for backup.
- `--region` has no default — it must be provided via CLI or `WASABI_REGION` when not using `--repository`.

## Local Development Workflow

Use this order when changing the repo:

1. Read `travel-backup-script.py` first. Nearly all behavior lives there.
2. Treat `README.md` as partially authoritative only after comparing it to the script.
3. If you change CLI flags, env loading, or repository construction, update code, README, and `.env.example` in the same change.
4. Preserve secret-handling behavior. Do not print raw credentials.

## Suggested Verification

Because the repo has no automated tests, prefer lightweight verification:

- Static review of argument parsing and env handling.
- Dry-run init:
  - `python travel-backup-script.py init --bucket <bucket> --region <region> --dry-run`
- Dry-run backup with a direct source:
  - `python travel-backup-script.py backup --source <path> --bucket <bucket> --region <region> --dry-run`
- Dry-run backup with a JSON config file:
  - `python travel-backup-script.py backup --file <config.json> --bucket <bucket> --region <region> --dry-run`

Avoid real backup runs unless the user explicitly asks for them and valid credentials are present.

## Editing Guidelines

- Keep the implementation as a simple single-file CLI unless the user asks for a larger refactor.
- Favor backwards-compatible flag changes where practical.
- Be careful with subprocess environment changes:
  - `PATH` must remain available so `restic` can be found.
  - `HOME` is intentionally forwarded when present.
  - On Windows, `SYSTEMROOT` and `COMSPEC` are required for DNS resolution and shell access.
- Do not commit real `.env.local` or other secret files.
- If adding tests later, prefer small CLI/unit tests around:
  - `build_repo`
  - `load_sources`
  - `resolve_repo` (priority order, validation)
  - missing `--bucket` handling
  - env minimization/redaction behavior

## Agent Notes

- Start discovery from the script, not the README.
- Keep `README.md`, `.env.example`, and the script aligned when flags change.
