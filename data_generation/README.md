# Synthetic Parquet data generation

[`generate_data.py`](generate_data.py) is the recovered generator used for the experiment. It writes one Snappy Parquet file at a time with seven transaction columns. The default seed is 42; the expanded series used a fixed 98-day window and explicit file indices, row offsets, and seeds for append batches.

Dependencies: Python, NumPy, Pandas, and PyArrow. The exact package versions from the CloudShell environment were not preserved in the source materials.

Example baseline generation:

```bash
python data_generation/generate_data.py \
  --rows 8400000 --files 12 --output-dir ./data/orders
```

Example of an append batch in the fixed date window:

```bash
python data_generation/generate_data.py \
  --rows 16800000 --files 24 --output-dir ./data/orders \
  --date-window-days 98 --file-index-start 12 \
  --row-offset 8400000 --seed 43
```
