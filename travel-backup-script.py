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

def run_restic(repo: str, source: str, dry_run: bool = False):
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
    for key in ("WASABI_ENDPOINT", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "RESTIC_PASSWORD"):
        if key in os.environ:
            print(f"  {key}=***REDACTED***")
    if dry_run:
        print("Dry-run mode: not running restic.")
        return 0
    return subprocess.call(cmd)

def main():
    # Load environment variables from .env.local (if present)
    load_dotenv(".env.local")

    parser = argparse.ArgumentParser(description="Backup files to Wasabi S3 with restic")
    parser.add_argument("--source", required=True, help="Path to file or directory to back up")
    parser.add_argument("--bucket", help="Wasabi S3 bucket name")
    parser.add_argument("--prefix", help="Prefix (folder) inside bucket", default=None)
    parser.add_argument("--region", default="us-east-1", help="Wasabi region, e.g. us-west-1")
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

    return run_restic(repo, args.source, args.dry_run)

if __name__ == "__main__":
    sys.exit(main())
