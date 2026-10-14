import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--files", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--date-window-days", type=int)
    parser.add_argument("--file-index-start", type=int, default=0)
    parser.add_argument("--row-offset", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.rows < args.files or args.files < 1:
        parser.error("--rows must be at least --files, and --files must be positive")
    if args.date_window_days is not None and args.date_window_days < 1:
        parser.error("--date-window-days must be positive")
    if args.file_index_start < 0 or args.row_offset < 0:
        parser.error("--file-index-start and --row-offset must be nonnegative")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(args.seed)

    rows_per_file, extra_rows = divmod(args.rows, args.files)
    offset = args.row_offset

    for file_index in range(args.files):
        count = rows_per_file + (1 if file_index < extra_rows else 0)
        first_timestamp = pd.Timestamp("2026-08-01") + pd.Timedelta(seconds=offset)

        if args.date_window_days is None:
            order_dates = pd.date_range(first_timestamp, periods=count, freq="s")
        else:
            window_seconds = args.date_window_days * 24 * 60 * 60
            seconds = (offset + np.arange(count, dtype=np.int64)) % window_seconds
            order_dates = pd.Timestamp("2026-08-01") + pd.to_timedelta(
                seconds, unit="s"
            )

        orders = pd.DataFrame({
            "order_date": order_dates,
            "region": np.random.choice(["US", "EU", "APAC"], count),
            "category": np.random.choice(
                ["electronics", "books", "home", "clothing"], count
            ),
            "status": np.random.choice(
                ["completed", "processing", "cancelled"],
                count,
                p=[0.6, 0.3, 0.1],
            ),
            "quantity": np.random.randint(1, 10, count),
            "unit_price": np.round(np.random.uniform(5.0, 200.0, count), 2),
            "customer_id": np.random.randint(1000, 9999, count),
        })

        path = args.output_dir / f"orders_part_{args.file_index_start + file_index:02d}.parquet"
        if path.exists():
            parser.error(f"Refusing to overwrite existing file: {path}")
        pq.write_table(
            pa.Table.from_pandas(orders, preserve_index=False),
            path,
            compression="snappy",
        )
        print(f"Wrote {count:,} rows to {path}")
        offset += count


if __name__ == "__main__":
    main()
