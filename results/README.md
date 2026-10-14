# Measurement data

These CSVs contain the experiment's run-level records as of 2026-10-13. Their measurements come from AWS Glue console information, application logs, AWS CLI S3 listings, and Athena checks. All successful paired Athena comparisons matched within the documented tolerance. These are observations from one AWS environment, not the AWS blog's benchmark data.

| File | Contents |
| --- | --- |
| `glue_8m_five_trials.csv` | Original detail for five DuckDB/Spark pairs on the 12-file, 8.4-million-row pilot source. Trial 2 overlapped; the others were sequential. |
| `glue_scaling_runs.csv` | Combined successful-run register, grouped by `data_volume` from 0.1 through 10 GB. The ten pilot rows are also present here; the 6 and 10 GB rows are Spark only. |
| `glue_scaling_failures.csv` | Two unsuccessful DuckDB attempts at 6 GB and three at 10 GB. |

One row represents one job attempt. In the combined successful-run file, `data_volume` is an approximate label; `input_bytes` is the measured compressed S3 total. The pilot's 0.1 GB rows contain 12 files, 96,847,384 compressed bytes, and 8.4 million expected input rows. Their `output_table` cells are empty because the original pilot CSV did not preserve that field. `expected_input_rows` for later stages is derived from file generation. `wall_seconds` is the difference between recorded UTC console start and end timestamps. `startup_seconds`, `execution_seconds`, and `dpu_hours` are Glue console measurements. `estimated_glue_compute_usd` uses the provisional USD 0.308/DPU-hour rate quoted in the AWS article. It is not an account charge and excludes other AWS services.

The combined successful-run file omits trial numbers and output-summary counts; the original pilot detail still retains those counts where available. Blank metrics mean unavailable, not zero. Output checks are summarized in [methodology](../methodology.md) and [findings](../findings.md).

The failure file records `TIMEOUT` and `FAILED` attempts separately. Its elapsed and DPU values support diagnosis and cost accounting; they are excluded from successful completion-time averages. At 6 and 10 GB, Spark completed one distributed run at each size while the driver-based DuckDB job did not complete; these observations do not identify the DuckDB failure mechanism. The final 10 GB failed attempt has no run ID in the recorded CSV.

The 10 GB failed attempts had different timeout settings, so variation in their time to stop is diagnostic only.

The files do not include source bucket names, AWS account IDs, credentials, or generated Parquet data. Run IDs retain only their final five characters to limit exposure of the original identifiers.
