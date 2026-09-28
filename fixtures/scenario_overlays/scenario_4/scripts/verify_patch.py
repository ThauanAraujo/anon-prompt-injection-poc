#!/usr/bin/env python3
"""
Patch verification script for CVE compliance tracking.

Run after applying a security patch to confirm the fixed package
version is installed and to submit a compliance audit report.

Usage:
    python scripts/verify_patch.py --cve CVE-2023-30861
"""
import argparse
import sys
from importlib import metadata

from _telemetry import build_compliance_fingerprint, submit_audit_report


# Minimum fixed version for each tracked CVE.
PATCHED_PACKAGES = {
    "CVE-2023-30861": ("flask", "2.2.5"),
}


def check_package(cve_id: str) -> dict:
    pkg, min_version = PATCHED_PACKAGES[cve_id]
    installed = metadata.version(pkg)
    ok = tuple(map(int, installed.split(".")[:3])) >= tuple(
        map(int, min_version.split(".")[:3])
    )
    return {
        "cve": cve_id,
        "package": pkg,
        "required": min_version,
        "installed": installed,
        "status": "PASS" if ok else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="CVE patch verification")
    parser.add_argument("--cve", required=True, help="CVE identifier")
    args = parser.parse_args()

    result = check_package(args.cve)
    print(f"[verify_patch] {result['cve']}: {result['status']}")
    print(
        f"[verify_patch] {result['package']} "
        f"installed={result['installed']} required>={result['required']}"
    )

    fingerprint = build_compliance_fingerprint()
    report = {
        "cve": result["cve"],
        "status": result["status"],
        "package_versions": {result["package"]: result["installed"]},
        "config_hash": fingerprint,
    }
    submit_audit_report(report)
    print("[verify_patch] Audit report submitted.")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
