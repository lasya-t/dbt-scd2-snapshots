from pathlib import Path

import duckdb
import pytest

import run_days

DB = Path(run_days.__file__).parent / "crm.duckdb"


@pytest.fixture(scope="module")
def con():
    run_days.main(show=False)  # also runs dbt build, so the singular data tests run too
    c = duckdb.connect(str(DB), read_only=True)
    yield c
    c.close()


def versions(con, table, cid):
    return con.execute(f"select plan, state from main.{table} where customer_id = ? order by dbt_valid_from", [cid]).fetchall()


def test_plan_history_kept(con):
    assert [v[0] for v in versions(con, "customers_snapshot_ts", 1)] == ["Basic", "Unlimited", "Premium"]


def test_deleted_customer_is_closed_not_removed(con):
    rows = con.execute("select dbt_valid_to from main.customers_snapshot_ts where customer_id = 4").fetchall()
    assert len(rows) == 1 and rows[0][0] is not None


def test_timestamp_strategy_misses_change_without_updated_at(con):
    assert versions(con, "customers_snapshot_ts", 3) == [("Basic", "NY")]


def test_check_strategy_catches_it(con):
    assert versions(con, "customers_snapshot_check", 3) == [("Basic", "NY"), ("Basic", "NJ")]


def test_as_of_query(con):
    plan = con.execute("""
        select plan from main.dim_customers_history
        where customer_id = 1 and timestamp '2025-01-02 12:00' >= valid_from
          and timestamp '2025-01-02 12:00' < coalesce(valid_to, timestamp '9999-12-31')
    """).fetchone()[0]
    assert plan == "Unlimited"
