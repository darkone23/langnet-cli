import polars as pl
import duckdb

# 1. Create a Polars DataFrame (Our "Source")
df_polars = pl.DataFrame({
    "name": ["Alice", "Bob", "Charlie", "David"],
    "points": [10, 45, 100, 20],
    "status": ["Bronze", "Silver", "Gold", "Bronze"]
})

# 2. Use DuckDB to run SQL directly on the Polars object
# DuckDB "sees" the df_polars variable in your local scope automatically.
query = """
    SELECT 
        status, 
        AVG(points) AS avg_points,
        COUNT(*) AS count
    FROM df_polars 
    WHERE points > 20
    GROUP BY status
"""

# 3. Execute and convert back to Polars
# .pl() is a native DuckDB method to output a Polars DataFrame
result = duckdb.sql(query).pl()

print("--- Query Result (Polars DataFrame) ---")
print(result)
