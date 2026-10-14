import logging
import os
import re
import sys
import time

import duckdb
from awsglue.utils import getResolvedOptions


TRANSFORM = """
SELECT
    CAST(order_date AS DATE) AS order_day,
    region,
    category,
    COUNT(*) AS total_orders,
    SUM(quantity * unit_price) AS gross_revenue,
    SUM(
        CASE WHEN status = 'completed'
             THEN quantity * unit_price ELSE 0 END
    ) AS net_revenue,
    COUNT(DISTINCT customer_id) AS unique_customers,
    ROUND(AVG(quantity * unit_price), 2) AS avg_order_value,
    SUM(
        CASE WHEN quantity * unit_price > 500
             THEN 1 ELSE 0 END
    ) AS high_value_orders
FROM read_parquet(?)
WHERE status IN ('completed', 'processing')
GROUP BY ALL
"""

CREATE_TARGET = """
CREATE TABLE IF NOT EXISTS {target} (
    order_day DATE,
    region VARCHAR,
    category VARCHAR,
    total_orders BIGINT,
    gross_revenue DOUBLE,
    net_revenue DOUBLE,
    unique_customers BIGINT,
    avg_order_value DOUBLE,
    high_value_orders BIGINT
)
"""


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logger = logging.getLogger(__name__)
    args = getResolvedOptions(sys.argv, ["s3_input_path", "s3t_arn", "target_table"])

    table_bucket_arn = args["s3t_arn"]
    table_name = args["target_table"]
    if not re.fullmatch(r"[a-z][a-z0-9_]*", table_name):
        raise ValueError("Invalid target table name")
    target = f"s3t.analytics.{table_name}"
    logger.info("input=%s target=%s duckdb=%s",
                args["s3_input_path"], target, duckdb.__version__)
    if not re.fullmatch(
        r"arn:aws:s3tables:[a-z0-9-]+:\d{12}:bucket/[a-z0-9-]+",
        table_bucket_arn,
    ):
        raise ValueError("Invalid S3 Tables table bucket ARN")

    os.makedirs("/tmp/.duckdb/extensions", exist_ok=True)
    con = duckdb.connect(":memory:")

    try:
        con.execute("SET home_directory='/tmp'")
        con.execute("SET extension_directory='/tmp/.duckdb/extensions'")

        for extension in ("httpfs", "aws", "iceberg"):
            con.execute(f"INSTALL {extension}")
            con.execute(f"LOAD {extension}")

        con.execute("CREATE SECRET (TYPE s3, PROVIDER credential_chain)")

        started = time.perf_counter()
        con.execute(f"CREATE TEMP TABLE _batch AS {TRANSFORM}", [args["s3_input_path"]])
        summary_rows, included_orders = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(total_orders), 0) FROM _batch"
        ).fetchone()
        logger.info(
            "Transform complete: summary_rows=%s included_orders=%s seconds=%.2f",
            summary_rows,
            included_orders,
            time.perf_counter() - started,
        )

        started = time.perf_counter()
        con.execute(
            f"ATTACH '{table_bucket_arn}' AS s3t "
            "(TYPE iceberg, ENDPOINT_TYPE s3_tables)"
        )
        con.execute(CREATE_TARGET.format(target=target))
        con.execute(
            f"DELETE FROM {target} "
            "WHERE order_day IN (SELECT DISTINCT order_day FROM _batch)"
        )
        con.execute(f"INSERT INTO {target} BY NAME SELECT * FROM _batch")

        output_rows = con.execute(f"SELECT COUNT(*) FROM {target}").fetchone()[0]
        logger.info(
            "Write complete: output_rows=%s seconds=%.2f",
            output_rows,
            time.perf_counter() - started,
        )
    finally:
        con.close()


if __name__ == "__main__":
    main()
