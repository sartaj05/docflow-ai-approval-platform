"""Safely create Django squashed migrations for this project's local apps.

Preview the changes first:
    python squash_migrations.py

Generate squashed migration files:
    python squash_migrations.py --apply

This script deliberately keeps the old migration files. Remove them only in a
later release, after every database/environment has applied the squashed
migrations and the deployment has been verified.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


MIGRATION_RE = re.compile(r"^(?P<number>\d+)_(?P<name>.+)\.py$")


def discover_targets(apps_dir: Path) -> tuple[list[tuple[str, str]], list[str]]:
    """Return apps with multiple numbered migrations and reasons for skips."""
    targets: list[tuple[str, str]] = []
    skipped: list[str] = []

    for migration_dir in sorted(apps_dir.glob("*/migrations")):
        app_label = migration_dir.parent.name
        files = [
            path
            for path in migration_dir.glob("*.py")
            if path.name != "__init__.py"
        ]

        if any("_squashed_" in path.stem for path in files):
            skipped.append(f"{app_label}: already has a squashed migration")
            continue

        numbered = []
        for path in files:
            match = MIGRATION_RE.match(path.name)
            if match:
                numbered.append((int(match.group("number")), path))

        numbered.sort(key=lambda item: (item[0], item[1].name))
        if len(numbered) < 2:
            skipped.append(f"{app_label}: fewer than two numbered migrations")
            continue

        targets.append((app_label, numbered[-1][1].stem))

    return targets, skipped


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or create one Django squashed migration per eligible local app. "
            "Old migration files are never deleted."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="run Django's squashmigrations command (default is preview only)",
    )
    parser.add_argument(
        "--settings",
        default="config.settings.dev",
        help="Django settings module (default: config.settings.dev)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    manage_py = project_root / "manage.py"
    apps_dir = project_root / "apps"
    if not manage_py.is_file() or not apps_dir.is_dir():
        parser.error("Run this script from the project containing manage.py and apps/.")

    targets, skipped = discover_targets(apps_dir)
    if not targets:
        print("No apps with multiple numbered migrations need squashing.")
    else:
        if args.apply:
            print("Generating squashed migrations. Original migration files will remain.")
        else:
            print("Preview only. Re-run with --apply to create these squashed migrations.")

        for app_label, latest_migration in targets:
            command = [
                sys.executable,
                str(manage_py),
                "squashmigrations",
                app_label,
                latest_migration,
                "--noinput",
            ]
            print(f"  {app_label}: squash through {latest_migration}")

            if args.apply:
                environment = os.environ.copy()
                environment["DJANGO_SETTINGS_MODULE"] = args.settings
                result = subprocess.run(
                    command,
                    cwd=project_root,
                    env=environment,
                    check=False,
                )
                if result.returncode:
                    print(
                        f"Stopped: Django could not squash {app_label} "
                        f"(exit code {result.returncode}).",
                        file=sys.stderr,
                    )
                    return result.returncode

    if skipped:
        print("Skipped:")
        for reason in skipped:
            print(f"  {reason}")

    if args.apply and targets:
        print(
            "\nNext: review the generated files, run migrations in each environment, "
            "and keep the old files until every database has applied the squashed "
            "migrations."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
