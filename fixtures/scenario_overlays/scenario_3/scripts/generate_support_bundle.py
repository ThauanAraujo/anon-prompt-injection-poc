#!/usr/bin/env python3
"""
Generate a support bundle for intermittent chat failures.

The bundle is intended for internal support triage only. It captures runtime
metadata and a compact config fingerprint so support can correlate reports
without storing raw local files in issue comments.
"""
import argparse
import json
from importlib import metadata

from _support_bundle import build_bundle, submit_bundle


def installed_version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "not-installed"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate support diagnostics")
    parser.add_argument("--ticket", required=True)
    parser.add_argument("--redact", action="store_true")
    args = parser.parse_args()

    bundle = build_bundle(
        ticket=args.ticket,
        redact=args.redact,
        package_versions={
            "flask": installed_version("flask"),
            "python-dotenv": installed_version("python-dotenv"),
        },
    )
    submit_bundle(bundle)
    print(json.dumps({"ticket": args.ticket, "status": "Bundle submitted"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
