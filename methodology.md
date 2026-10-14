# Experimental methodology

## Study design

This study extends the single-volume ETL comparison in the [AWS Big Data Blog](https://aws.amazon.com/blogs/big-data/cost-effective-etl-with-duckdb-and-amazon-s3-tables-on-aws-glue/) into a fixed-capacity scaling series. Its question is how elapsed job time and estimated Glue compute cost change as compressed Parquet input grows. It assesses a particular implementation and configuration, not the intrinsic performance of either engine across all workloads.

| Role | Variable | Operational definition |
| --- | --- | --- |
| Independent | Input volume | Sum of compressed bytes of the S3 Parquet objects read by both jobs, reported in decimal GB; file count and expected row count are also recorded. |
| Dependent | Job duration (wall time) | UTC job end time minus UTC job start time (`wall_seconds`), reported separately from Glue startup and execution times. Only successful jobs enter completion-time summaries. |
| Dependent | Glue compute cost | Reported DPU-hours multiplied by a provisional USD 0.308/DPU-hour. Failed attempts retain their own estimated cost. |
| Controlled | Source and transformation | Same source object set within each size, seven-column schema, Snappy Parquet format, 98-day date window for the expanded series, exclusion of cancelled orders, and equivalent output metrics. |
| Controlled | Glue capacity | Glue 6.0, `us-east-1`, two G.1X workers (two allocated DPUs) per job. |
| Controlled | Output state | A separate empty Iceberg output table for each engine and trial, so each successful comparison is a first write. |
| Recorded | Run conditions | Engine order, masked Glue run ID, timestamps, startup/execution time, DPU-hours, and failure status. Output checks are described separately. |

The input ladder was approximately 0.1, 0.3, 1, 3, 4.5, 6, and 10 GB. The five successful-volume stages each have five paired trials; 6 and 10 GB have one successful Spark run each and no completed DuckDB run. The initial 0.097 GB stage is a pilot: trial 2 overlapped in time and is retained visibly rather than silently removed. Later pairs ran sequentially, with the starting engine alternated where practical. Both engines used the same frozen source objects at a given size.

## Dataset and workload controls

The generator writes approximately 700,000 rows per file with a fixed seed policy and the columns `order_date`, `region`, `category`, `status`, `quantity`, `unit_price`, and `customer_id`. The expanded series keeps dates in a 98-day window beginning 2026-08-01. More input rows therefore do not increase the possible number of day-region-category groups. This controls output cardinality while measuring greater input volume. The dataset remains synthetic; it is not a representative sample of all production distributions.

The original 12-file pilot contains 8.4 million rows and 96,847,384 compressed bytes. Expected row totals for later stages come from the generator's 700,000-row-per-file setting and the recorded file counts. The measured compressed byte counts, rather than nominal stage names or expected row totals, define the x-axis.

Both implementations perform the same intended business aggregation and write to separate S3 Tables Iceberg tables. The [local Spark script](jobs/spark_order_summary.py) implements the equivalent transformation for this comparison. The AWS article describes its Spark job but does not include a complete Spark script there to establish that its code matches ours. Engine-specific read and write mechanisms differ. Equal Glue worker allocation is an experimental control, but it does not imply equal use of each worker: DuckDB executes in the Glue driver, whereas Spark distributes work. The findings therefore describe this **fixed allocated capacity**, not the best configuration for each engine.

## Measurement and cost calculations

Each successful CSV row is an observed Glue job run. `wall_seconds` comes from the recorded console start and end timestamps. `startup_seconds`, `execution_seconds`, and `dpu_hours` are Glue's displayed measurements; rounded values can differ slightly from the timestamp difference. Application `transform_seconds` and `write_seconds` are present only when logs supplied them. Blank fields mean unavailable, not zero.

Estimated Glue compute cost per run is:

```text
reported DPU-hours × USD 0.308 per DPU-hour
```

This provisional rate comes from the published AWS example and needs confirmation against the applicable price and account billing record before being presented as actual spend. The estimate excludes S3 storage and requests, S3 Tables, Athena validation queries, CloudWatch, and any other AWS charges. For each input volume and engine, successful-run job duration, Glue-reported execution time, and cost can be summarized with the arithmetic mean, median, sample standard deviation (denominator `n − 1`), coefficient of variation (`100 × sample standard deviation / mean`), and observed minimum–maximum range. These are descriptive statistics, not confidence intervals. At 6 and 10 GB, Spark has only one completed run per volume, so its sample standard deviation and coefficient of variation are undefined. Individual runs remain in the CSVs so variation is visible.

Failures are analyzed as **completion failures**, not slow successful runs. Their elapsed time and estimated cost receive separate descriptive summaries for diagnostic and spending analysis; elapsed time means **time to stop**, not time to complete the ETL. At 6 and 10 GB, Spark's completed runs demonstrate a useful alternative execution pattern for this fixed-capacity workload: it distributes tasks while this DuckDB implementation runs in the driver. The evidence does not identify which resource or operation caused the DuckDB failures. The 10 GB attempts used different timeout caps, so dispersion of their time to stop is not a performance variability estimate. A 10-minute timeout gives a lower bound on time required to complete under that cap, not a DuckDB completion time. A process exit with code 137 indicates a forced termination; memory exhaustion is a hypothesis, not a confirmed diagnosis.

## Output checks and validity

All paired outputs were reviewed in Athena by day, region, and category. Counts matched exactly across all pairs, with no missing or differing groups; floating-point measures matched within an absolute tolerance of 0.01.

The AWS article's reported numbers are a reference point, not observations in this series. Exact generated records and run-level conditions differ; the article does not provide a complete Spark script there for code-equivalence verification. This study is an **experimental extension of the AWS case**, not an exact reproduction of AWS's measurements.

## Included materials

The repository contains run-level observations, the experimental method, the owner-supplied DuckDB and Spark scripts, a data generator, and sanitized Glue job definitions with the DuckDB dependency pin and Spark catalog arguments. The measurements can be calculated from the CSVs.
