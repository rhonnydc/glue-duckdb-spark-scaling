# AWS Glue ETL jobs

This directory contains the DuckDB and PySpark ETL scripts supplied with the experiment:

| File | Engine | Glue arguments |
| --- | --- | --- |
| [`duckdb_order_summary.py`](duckdb_order_summary.py) | DuckDB 1.5.1 in the Glue driver | `--s3_input_path`, `--s3t_arn`, `--target_table` |
| [`spark_order_summary.py`](spark_order_summary.py) | PySpark in Glue 6.0 | `--s3_input_path`, `--target_table` |

Both scripts read the S3 Parquet source, retain completed and processing orders, aggregate by day, region, and category, and write Iceberg tables in Amazon S3 Tables. The local Spark script implements the equivalent transformation for this comparison. The AWS article describes a Spark job, but does not publish a complete Spark script there that would establish identical code. DuckDB loads the `httpfs`, `aws`, and `iceberg` extensions; Spark uses the Iceberg catalog configured in the Glue job definition. Both perform a `DELETE` followed by an `INSERT` for affected days; these are separate commits, so interrupted-write recovery has not been established.

The accompanying sanitized Glue definitions are in [`configs/`](../configs/). The measured behavior and output contract are documented in [methodology](../methodology.md) and the [run records](../results/README.md). The scripts were supplied by the experiment owner.
