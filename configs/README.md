# AWS Glue configuration

Known settings for the measured series:

| Setting | Recorded value |
| --- | --- |
| AWS Region | `us-east-1` |
| AWS Glue version | 6.0 |
| Job type | `glueetl` |
| Worker type | G.1X |
| Workers per job | 2 |
| Allocated capacity | 2 DPUs |
| DuckDB package | 1.5.1, installed through Glue's additional Python modules |
| Maximum concurrent runs | 1 per job |
| Default retry count | 0 |
| Exported timeout | 10 minutes per job; some diagnostic attempts used other caps |
| Input | Snappy Parquet objects in Amazon S3 |
| Output | Separate Apache Iceberg tables in Amazon S3 Tables |

The source path and destination table were passed as job arguments. Fresh target tables were used for paired trials. Timeout settings changed for diagnostic DuckDB attempts at 10 GB and were recorded in the failure data.

Job exports are represented by [`job-duckdb.sanitized.json`](job-duckdb.sanitized.json) and [`job-spark.sanitized.json`](job-spark.sanitized.json). They preserve the Glue version, worker allocation, command type, concurrency, timeout, retry count, dependency arguments, and Spark Iceberg catalog settings.

The JSON files are reference copies, not directly deployable definitions. Replace each placeholder with values from the intended AWS environment and upload the corresponding script before creating a new job. See [methodology](../methodology.md) for the variables held constant in the measured series.
