import argparse
import subprocess
import os
import sys
from shutil import which
from dotenv import load_dotenv


def build_repo(endpoint: str, bucket: str, prefix: str) -> str:
    """
    Build a restic S3 repository URL in the correct format:
    s3:ENDPOINT/BUCKET/PREFIX
    """
    parts = [f"s3:{endpoint.rstrip('/')}"]
    if bucket:
        parts.append(bucket.strip("/"))
    if prefix:
        parts.append(prefix.strip("/"))
    return "/".join(parts)


def redact_env(env: dict) -> dict:
    """Return a copy of env with secrets redacted."""
    redacted = env.copy()
    for k in ("AWS_SECRET_ACCESS_KEY", "RESTIC_PASSWORD", "AWS_SECRET_KEY"):
        if k in redacted and redacted[k]:
            redacted[k] = "***REDACTED***"
    return redacted


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Backup files to a Wasabi (S3) bucket using restic."
    )
    parser.add_argument("--source", "-s", required=True,
                        help="Source path to back up (file or directory)")
    parser.add_argument("--bucket", "-b",
                        help="Wasabi bucket name (can be omitted if --repository is used)")
    parser.add_argument("--endpoint", "-e",
                        default=os.environ.get("WASABI_ENDPOINT", "s3.wasabisys.com"),
                        help="Wasabi S3 endpoint host (default: s3.wasabisys.com or WASABI_ENDPOINT env)")
    parser.add_argument("--prefix", "-p",
                        default=os.environ.get("RESTIC_PREFIX", "travel-backup"),
                        help="Prefix/path inside the bucket (default: travel-backup)")
    parser.add_argument("--access-key",
                        help="Wasabi access key (falls back to .env or AWS_ACCESS_KEY_ID env)")
    parser.add_argument("--secret-key",
                        help="Wasabi secret key (falls back to .env or AWS_SECRET_ACCESS_KEY env)")
    parser.add_argument("--password", "-P",
                        help="Restic repository password (falls back to .env or RESTIC_PASSWORD env)")
    parser.add_argument("--repository", "-r",
                        help="Full restic repository string (overrides bucket+endpoint+prefix)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the restic command and environment without running it")
    parser.add_argument("--verbose", action="store_true", help="Show more output")
    parser.add_argument("--env-file", default=".env",
                        help="Path to .env file (default: .env)")

    args = parser.parse_args(argv)

    # Load env file (if it exists)
    if os.path.exists(args.env_file):
        load_dotenv(args.env_file)

    # Validate source path
    src = args.source
    if not os.path.exists(src):
        print(f"error: source path does not exist: {src}")
        return 2

    # Build repository string
    if args.repository:
        repo = args.repository
    else:
        if not args.bucket:
            print("error: --bucket is required when --repository is not provided")
            return 2
        repo = build_repo(args.endpoint, args.bucket, args.prefix)

    # Prepare environment
    env = os.environ.copy()

    # Apply CLI > env > .env precedence
    if args.password:
        env["RESTIC_PASSWORD"] = args.password
    if args.access_key:
        env["AWS_ACCESS_KEY_ID"] = args.access_key
    if args.secret_key:
        env["AWS_SECRET_ACCESS_KEY"] = args.secret_key

    # Validation: ensure critical vars exist
    missing = []
    for var in ("RESTIC_PASSWORD", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        if not env.get(var):
            missing.append(var)
    if missing:
        print(f"error: missing required environment variables: {', '.join(missing)}")
        print(f"tip: define them in {args.env_file} or pass as CLI args")
        return 2

    # Ensure restic is installed
    if which("restic") is None:
        print("error: restic binary not found in PATH. Install restic and try again.")
        return 3

    cmd = ["restic", "-r", repo, "backup", src]

    if args.verbose or args.dry_run:
        print("Repository:", repo)
        print("Command:", " ".join(cmd))
        print("Environment (redacted):")
        for k, v in redact_env(env).items():
            if k.startswith("AWS_") or k.startswith("RESTIC_") or k in ("WASABI_ENDPOINT",):
                print(f"  {k}={v}")

    if args.dry_run:
        print("Dry-run mode: not running restic.")
        return 0

    # Run restic
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    except Exception as exc:
        print("error: failed to run restic:", exc)
        return 4

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
