#!/usr/bin/env python3
import argparse
import os
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

def run_restic(repo: str, source: str, dry_run: bool = False, env: dict = None):
    """Run restic backup command."""
    cmd = [
        "restic",
        "-r", repo,
        "backup",
        source,
    ]
    
    print("Repository:", repo)
    print("Command:", " ".join(cmd))
    print("Environment (redacted):")
    
    # Use provided env or fall back to current process env
    if env is None:
        env = os.environ.copy()

    # Check which env vars are available in the environment we're passing to restic
    env_vars = ("WASABI_ENDPOINT", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "RESTIC_PASSWORD")
    for key in env_vars:
        if key in env and env.get(key) is not None:
            print(f"  {key}=***REDACTED***")
        else:
            print(f"  {key}=NOT SET")
    
    if dry_run:
        print("Dry-run mode: not running restic.")
        return 0
    
    # Pass the provided environment explicitly to the restic subprocess
    return subprocess.call(cmd, env=env)

def main():
    # Load environment variables from .env.local (if present)
    load_dotenv(".env.local")
    
    parser = argparse.ArgumentParser(description="Backup files to Wasabi S3 with restic")
    parser.add_argument("--source", required=True, help="Path to file or directory to back up")
    parser.add_argument("--bucket", help="Wasabi S3 bucket name")
    parser.add_argument("--prefix", help="Prefix (folder) inside bucket", default=None)
    parser.add_argument("--region", default="us-west-1", help="Wasabi region, e.g. us-west-1")
    parser.add_argument("--repository", help="Full restic repository string (overrides bucket/prefix)")
    parser.add_argument("--dry-run", action="store_true", help="Print command instead of running it")
    
    args = parser.parse_args()
    
    # Endpoint based on region (unless already set in env)
    endpoint = os.getenv("WASABI_ENDPOINT", f"s3.{args.region}.wasabisys.com")
    
    # Build repo string
    if args.repository:
        repo = args.repository
    else:
        if not args.bucket:
            print("error: --bucket is required when --repository is not provided")
            return 2
        repo = build_repo(endpoint, args.bucket, args.prefix)
    
    # Capture the current process environment (including values loaded by load_dotenv)
    proc_env = os.environ.copy()

    # Build a minimal env dict to pass to restic. Include only the keys restic needs
    # plus PATH and HOME so the restic binary can be resolved and user context is preserved.
    needed_keys = ("WASABI_ENDPOINT", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "RESTIC_PASSWORD")
    minimal_env = {}
    for k in needed_keys:
        v = proc_env.get(k)
        if v is not None:
            minimal_env[k] = v

    # Ensure WASABI_ENDPOINT is provided (use computed endpoint fallback)
    if "WASABI_ENDPOINT" not in minimal_env or not minimal_env.get("WASABI_ENDPOINT"):
        minimal_env["WASABI_ENDPOINT"] = endpoint

    # Preserve PATH and HOME so subprocess can find restic and use user's home directory
    minimal_env["PATH"] = proc_env.get("PATH", "")
    if proc_env.get("HOME") is not None:
        minimal_env["HOME"] = proc_env.get("HOME")

    return run_restic(repo, args.source, args.dry_run, env=minimal_env)

if __name__ == "__main__":
    sys.exit(main())