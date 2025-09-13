from __future__ import annotations

import subprocess


def main() -> int:
    """
    Amend the last commit with the updated coverage
    """
    # Check if the coverage badge has changed
    diff = subprocess.run(["git", "diff", "--quiet", "--", "badges/coverage.svg"])
    # If the coverage badge has changed, amend the last commit with the updated coverage badge
    if diff.returncode != 0:
        subprocess.run(["git", "add", "badges/coverage.svg"], check=True)
        subprocess.run(["git", "commit", "--amend", "--no-edit"], check=False)
    # Return success code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
