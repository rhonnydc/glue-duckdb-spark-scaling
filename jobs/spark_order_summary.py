import logging
import re
import sys
import time

from awsglue.utils import getResolvedOptions
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


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
FROM orders
WHERE status IN ('completed', 'processing')
GROUP BY CAST(order_date AS DATE), region, category
"""

COLUMNS = """
    order_day, region, category, total_orders, gross_revenue,
    net_revenue, unique_customers, avg_order_value, high_value_orders
"""


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logger = logging.getLogger(__name__)
    args = getResolvedOptions(sys.argv, ["s3_input_path", "target_table"])

    table_name = args["target_table"]
    if not re.fullmatch(r"[a-z][a-z0-9_]*", table_name):
        raise ValueError("Invalid target table name")
    target = f"s3t.analytics.{table_name}"

    spark = SparkSession.builder.appName("spark-order-summary").getOrCreate()
    spark.conf.set("spark.sql.session.timeZone", "UTC")

    try:
        started = time.perf_counter()
        spark.read.parquet(args["s3_input_path"]).createOrReplaceTempView("orders")
        batch = spark.sql(TRANSFORM).cache()
        batch.createOrReplaceTempView("_batch")

        metrics = batch.agg(
            F.count("*").alias("summary_rows"),
            F.sum("total_orders").alias("included_orders"),
        ).first()
        logger.info(
            "Transform complete: summary_rows=%s included_orders=%s seconds=%.2f",
            metrics["summary_rows"],
            metrics["included_orders"],
            time.perf_counter() - started,
        )

        started = time.perf_counter()
        spark.sql(f"""
            CREATE TABLE IF NOT EXISTS {target} (
                order_day DATE,
                region STRING,
                category STRING,
                total_orders BIGINT,
                gross_revenue DOUBLE,
                net_revenue DOUBLE,
                unique_customers BIGINT,
                avg_order_value DOUBLE,
                high_value_orders BIGINT
            ) USING iceberg
        """)
        spark.sql(f"""
            DELETE FROM {target}
            WHERE order_day IN (SELECT DISTINCT order_day FROM _batch)
        """)
        spark.sql(f"INSERT INTO {target} ({COLUMNS}) SELECT {COLUMNS} FROM _batch")

        output_rows = spark.table(target).count()
        logger.info(
            "Write complete: output_rows=%s seconds=%.2f",
            output_rows,
            time.perf_counter() - started,
        )
        batch.unpersist()
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
