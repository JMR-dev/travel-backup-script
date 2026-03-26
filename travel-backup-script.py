#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from dotenv import load_dotenv

def build_repo(endpoint: str, bucket: str, prefix: str = None) -> str:
    """
    Build a restic S3 repository URL in the correct format:
    s3:ENDPOINT/BUCKET[/PREFIX]
    """
    parts = [f"s3:{endpoint.rstrip('/')}"]
    if bucket:
        parts.append(bucket.strip("/"))
    if prefix:
        parts.append(prefix.strip("/"))
    return "/".join(parts)

def load_sources(source: str = None, source_file: str = None) -> list[str]:
    """Resolve backup sources from --source or a JSON file."""
    if source is not None:
        return [source]

    with open(source_file, "r", encoding="utf-8") as fh:
        config = json.load(fh)

    paths = config.get("paths")
    if not isinstance(paths, list) or not paths:
        raise ValueError('config file must contain a non-empty "paths" array')
    if not all(isinstance(path, str) and path.strip() for path in paths):
        raise ValueError('each entry in "paths" must be a non-empty string')

    return paths

def print_env_status(env: dict):
    """Print redacted environment variable status."""
    env_vars = ("WASABI_ENDPOINT", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "RESTIC_PASSWORD")
    for key in env_vars:
        if key in env and env.get(key) is not None:
            print(f"  {key}=***REDACTED***")
        else:
            print(f"  {key}=NOT SET")

def run_restic(repo: str, sources: list[str], dry_run: bool = False, env: dict = None, source_file: str = None):
    """Run restic backup command."""
    cmd = [
        "restic",
        "-r", repo,
        "backup",
        *sources,
    ]

    print("Repository:", repo)
    print("Command:", " ".join(cmd))
    print("Environment (redacted):")

    # Use provided env or fall back to current process env
    if env is None:
        env = os.environ.copy()

    print_env_status(env)

    if dry_run:
        if source_file:
            print("Config file:", source_file)
        print("Dry-run mode: not running restic.")
        return 0

    # Pass the provided environment explicitly to the restic subprocess
    subprocess.check_call(cmd, env=env)
    return 0

def run_restic_init(repo: str, dry_run: bool = False, env: dict = None):
    """Run restic init command to initialize a new repository."""
    cmd = [
        "restic",
        "-r", repo,
        "init",
    ]

    print("Initializing repository:", repo)
    print("Command:", " ".join(cmd))
    print("Environment (redacted):")

    if env is None:
        env = os.environ.copy()

    print_env_status(env)

    if dry_run:
        print("Dry-run mode: not running restic.")
        return 0

    subprocess.check_call(cmd, env=env)
    return 0

def resolve_repo(args) -> str:
    """Resolve the restic repository string from args and environment."""
    # CLI --repository takes priority, then RESTIC_REPOSITORY env var
    repository = getattr(args, "repository", None) or os.getenv("RESTIC_REPOSITORY")
    if repository:
        if not re.match(r"^s3:s3\.[a-z0-9-]+\.wasabisys\.com/.+", repository):
            print(f"error: repository '{repository}' does not match expected format: s3:s3.<region>.wasabisys.com/<bucket>[/<prefix>]")
            return None
        return repository

    bucket = getattr(args, "bucket", None) or os.getenv("WASABI_BUCKET")
    if not bucket:
        print("error: --bucket or WASABI_BUCKET is required when --repository / RESTIC_REPOSITORY is not provided")
        return None

    region = getattr(args, "region", None) or os.getenv("WASABI_REGION")
    if not region:
        print("error: --region or WASABI_REGION is required when --repository / RESTIC_REPOSITORY is not provided")
        return None

    endpoint = os.getenv("WASABI_ENDPOINT", f"s3.{region}.wasabisys.com")
    # CLI --prefix takes priority, then RESTIC_PREFIX env var
    prefix = getattr(args, "prefix", None) or os.getenv("RESTIC_PREFIX")
    return build_repo(endpoint, bucket, prefix)

def build_minimal_env() -> dict:
    """Build a minimal env dict to pass to restic subprocesses."""
    proc_env = os.environ.copy()

    needed_keys = ("WASABI_ENDPOINT", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "RESTIC_PASSWORD")
    minimal_env = {}
    for k in needed_keys:
        v = proc_env.get(k)
        if v is not None:
            minimal_env[k] = v

    # Preserve system env vars needed by subprocesses
    # PATH/HOME: find restic and resolve home directory
    # SYSTEMROOT/COMSPEC: required on Windows for DNS resolution and shell access
    system_keys = ("PATH", "HOME", "SYSTEMROOT", "SystemRoot", "COMSPEC")
    for k in system_keys:
        v = proc_env.get(k)
        if v is not None:
            minimal_env[k] = v

    return minimal_env

def main():
    # Load environment variables from .env.local (if present)
    load_dotenv(".env.local")

    parser = argparse.ArgumentParser(description="Backup files to Wasabi S3 with restic")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Shared repo arguments
    repo_args = argparse.ArgumentParser(add_help=False)
    repo_args.add_argument("--bucket", help="Wasabi S3 bucket name (or set WASABI_BUCKET)")
    repo_args.add_argument("--prefix", help="Prefix (folder) inside bucket (or set RESTIC_PREFIX)", default=None)
    repo_args.add_argument("--region", default=None, help="Wasabi region, e.g. us-west-1 (or set WASABI_REGION)")
    repo_args.add_argument("--repository", help="Full restic repository string (or set RESTIC_REPOSITORY)")
    repo_args.add_argument("--dry-run", action="store_true", help="Print command instead of running it")

    # init subcommand
    subparsers.add_parser("init", parents=[repo_args], help="Initialize a new restic repository")

    # backup subcommand
    backup_parser = subparsers.add_parser("backup", parents=[repo_args], help="Run a backup")
    source_group = backup_parser.add_mutually_exclusive_group(required=False)
    source_group.add_argument("--source", "-s", help="Path to file or directory to back up")
    source_group.add_argument("--file", "-f", help='Path to a JSON config file containing {"paths": [...]} (or set FILE_PATH_CONFIG_PATH)')

    args = parser.parse_args()

    repo = resolve_repo(args)
    if repo is None:
        return 2

    minimal_env = build_minimal_env()

    try:
        if args.command == "init":
            return run_restic_init(repo, args.dry_run, env=minimal_env)

        # backup command — resolve file path from CLI or env var
        source_file = args.file or os.getenv("FILE_PATH_CONFIG_PATH")
        if not args.source and not source_file:
            print("error: --source, --file, or FILE_PATH_CONFIG_PATH is required for backup")
            return 2

        sources = load_sources(args.source, source_file)
        return run_restic(repo, sources, args.dry_run, env=minimal_env, source_file=source_file)
    except subprocess.CalledProcessError as exc:
        print(f"error: restic exited with code {exc.returncode}: {exc}", file=sys.stderr)
        return exc.returncode
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}")
        return 2

if __name__ == "__main__":
    sys.exit(main())
