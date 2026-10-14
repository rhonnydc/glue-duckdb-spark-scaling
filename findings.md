# Findings and limitations

## Interpretation

With AWS Glue 6.0, two G.1X workers per job, and the measured synthetic workload, both implementations completed every paired trial through 4.503 GB of compressed Parquet input. DuckDB had lower **average job duration (start to finish), or wall time**, and lower estimated Glue compute cost at each of those five sizes. The difference in average job duration ranged from approximately 41% to 49% across the successful paired stages. Estimated compute cost per completed job was approximately 41% to 51% lower for DuckDB at those stages.

At 6.005 GB, Spark completed one run in 377 seconds while both DuckDB attempts failed. At 10.072 GB, Spark completed one run in 605 seconds while DuckDB had two timeouts and one failed process exit. Their execution models matter when choosing an engine: Spark can share processing across workers, whereas the tested DuckDB job relies on the Glue driver. This supports testing Spark when similar workloads grow beyond the range where DuckDB completed successfully. It does not establish an exact capacity threshold or show that the execution model caused the failures.

The five DuckDB non-completions consumed an estimated $1.293 of Glue compute at the provisional rate, without a completed output. This matters when evaluating practical cost: a low cost per successful run is useful only where the job completes reliably. For larger or more demanding jobs, Spark's distributed execution may be the more dependable choice under the tested capacity. Failed attempt time is not plotted or averaged as ETL completion time.

All successful DuckDB/Spark output pairs were checked in Athena by day, region, and category. Counts and groups matched; floating-point measures matched within an absolute tolerance of 0.01. The 6 and 10 GB stages have no completed DuckDB output to compare; Spark's completed runs there support testing its distributed approach for similar larger jobs.

## Practical cost implication

A company that deliberately routes suitable, repeatable Glue jobs to DuckDB **could reduce its total Glue compute spending by a substantial percentage**. The opportunity is real in this experiment: eligible completed jobs had about 41%–51% lower estimated compute cost with DuckDB. For illustration, if half of a company's Glue compute spending were on jobs that could consistently achieve a 45% reduction, its overall Glue compute spending would fall by about 22.5%, before migration effort or other charges. This is a conditional scenario, not a measured company-wide saving or a guarantee. The company must test each job's input size, transformations, concurrency, output correctness, failure rate, recovery needs, and growth. Jobs needing distributed execution may be better kept on Spark.

The following **estimated** monthly spending bands adapt an illustrative company-profile table supplied for this project. All costs are recalculated using the same provisional rate as the experiment, USD 0.308 per DPU-hour (`DPU-hours × 0.308`). Company size does not determine DPU use: actual spending depends on the number, duration, complexity, configuration, and frequency of its jobs, as well as region and applicable pricing. These are not observations from companies or actual billed amounts. The estimate covers Glue compute only.

| Illustrative company profile | Estimated DPU-hours/month | Estimated monthly Glue compute cost at USD 0.308/DPU-hour |
| --- | ---: | ---: |
| Startup / small company | 50–300 | USD 15.40–92.40 |
| Small or medium company with recurring pipelines | 300–1,500 | USD 92.40–462 |
| Medium company | 1,500–6,000 | USD 462–1,848 |
| Large company | 6,000–25,000 | USD 1,848–7,700 |
| Enterprise with intensive use | 25,000–100,000+ | USD 7,700–30,800+ |

## Limits of the inference

- This is a **fixed allocated capacity** comparison. DuckDB runs in the Glue driver; Spark uses distributed execution. Two allocated DPUs do not imply identical resource use or each engine's best configuration.
- There are five successful pairs per volume through 4.503 GB, but only one Spark completion at 6 GB and one at 10 GB. Dispersion at those larger volumes cannot be estimated. The 0.097 GB pilot includes one overlapping pair.
- The synthetic dataset keeps a common schema, major distributions, and a fixed 98-day window as volume grows. Other distributions, file layouts, or transformations could produce different scaling behavior.
- The [local Spark script](jobs/spark_order_summary.py) implements an equivalent transformation for our comparison. The original AWS article describes its Spark job but does not provide a complete Spark script there to establish code identity. These are this project's observations, an experimental extension of the AWS case rather than a reproduction of its published run times.
- The cost figures cover estimated Glue compute only. S3, S3 Tables, Athena, logs, and other charges are outside the calculation, and the provisional rate has not been reconciled to the account bill.
- The available evidence does not establish whether memory pressure, I/O, spilling, or another mechanism caused the 6 and 10 GB DuckDB failures. Spark's distributed processing completed one run at each of those sizes, which supports evaluating Spark for workloads beyond DuckDB's observed successful range here. Exit code 137 alone does not identify the root cause.
- The DuckDB implementation uses separate `DELETE` and `INSERT` commits for affected dates. Interrupted-write recovery and idempotency were not established by this scaling series.

See [methodology](methodology.md) and [individual job records](results/README.md) for the supporting measurements.
