"""Replay three days of source changes, taking a dbt snapshot after each, then compare strategies."""
import os
import subprocess
from pathlib import Path

import duckdb

from source_system import DAYS, apply_day

ROOT = Path(__file__).parent
DB = str(ROOT / "crm.duckdb")


def dbt(*args):
    env = {**os.environ, "DBT_PROFILES_DIR": str(ROOT)}
    r = subprocess.run(["dbt", *args, "--quiet"], cwd=ROOT, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)


def main(show=True):
    if os.path.exists(DB):
        os.remove(DB)
    for day in DAYS:
        apply_day(DB, day)
        dbt("snapshot")
    dbt("build", "--exclude", "resource_type:snapshot")
    if not show:
        return
    con = duckdb.connect(DB, read_only=True)
    for name in ("customers_snapshot_ts", "customers_snapshot_check"):
        df = con.sql(f"""
            select customer_id, name, state, plan,
                   strftime(dbt_valid_from, '%m-%d %H:%M') as valid_from,
                   coalesce(strftime(dbt_valid_to, '%m-%d %H:%M'), 'current') as valid_to
            from main.{name} order by customer_id, dbt_valid_from
        """).df()
        print(f"\n=== {name}: {len(df)} versions for {df.customer_id.nunique()} customers")
        print(df.to_string(index=False))
    print("\n=== plan held by each customer at 2025-01-02 12:00 (as-of query on dim_customers_history)")
    print(con.sql("""
        select customer_id, name, plan, state from main.dim_customers_history
        where timestamp '2025-01-02 12:00' >= valid_from
          and timestamp '2025-01-02 12:00' <  coalesce(valid_to, timestamp '9999-12-31')
        order by customer_id
    """).df().to_string(index=False))


if __name__ == "__main__":
    main()
