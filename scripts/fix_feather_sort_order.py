#!/usr/bin/env python3
"""Fix reverse chronological ordering in feather files.

Re-sorts all -futures.feather and -mark.feather files in gmx_complete/futures/
to ascending chronological order (oldest first).
"""

from pathlib import Path

import pandas as pd
import pyarrow.feather as feather

BASE_DIR = Path(__file__).resolve().parent.parent
TARGET_DIR = BASE_DIR / "user_data" / "data" / "gmx_complete" / "futures"


def main() -> None:
    patterns = ["*-futures.feather", "*-mark.feather"]
    files = []
    for pattern in patterns:
        files.extend(sorted(TARGET_DIR.glob(pattern)))

    print(f"Found {len(files)} files to check in {TARGET_DIR}")

    fixed = 0
    already_ok = 0

    for filepath in files:
        df = pd.read_feather(filepath)
        if df.empty or len(df) < 2:
            already_ok += 1
            continue

        if df["date"].is_monotonic_increasing:
            already_ok += 1
            continue

        df = df.sort_values("date").reset_index(drop=True)
        feather.write_feather(df, filepath)
        fixed += 1

    print(f"Fixed:      {fixed}")
    print(f"Already OK: {already_ok}")
    print("Done!")


if __name__ == "__main__":
    main()
