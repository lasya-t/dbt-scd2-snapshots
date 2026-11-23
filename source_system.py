"""Plays the role of the operational CRM database that dbt snapshots read from.

Each "day" applies changes to crm_src.customers the way an app would:
updates overwrite the row in place (no history), and closed accounts are deleted.
"""
from __future__ import annotations

import duckdb

DAYS = {
    "2025-01-01": [
        "CREATE SCHEMA IF NOT EXISTS crm_src",
        "CREATE OR REPLACE TABLE crm_src.customers (customer_id INT, name VARCHAR, state VARCHAR, plan VARCHAR, updated_at TIMESTAMP)",
        """INSERT INTO crm_src.customers VALUES
            (1, 'Ana',  'PA', 'Basic',     '2025-01-01 09:00'),
            (2, 'Raj',  'NJ', 'Unlimited', '2025-01-01 09:00'),
            (3, 'Mei',  'NY', 'Basic',     '2025-01-01 09:00'),
            (4, 'Omar', 'DE', 'Premium',   '2025-01-01 09:00')""",
    ],
    "2025-01-02": [
        # Ana upgrades; Raj moves to PA; a new customer signs up
        "UPDATE crm_src.customers SET plan = 'Unlimited', updated_at = '2025-01-02 10:15' WHERE customer_id = 1",
        "UPDATE crm_src.customers SET state = 'PA', updated_at = '2025-01-02 14:30' WHERE customer_id = 2",
        "INSERT INTO crm_src.customers VALUES (5, 'Lena', 'NJ', 'Basic', '2025-01-02 16:00')",
    ],
    "2025-01-03": [
        # Ana upgrades again; Omar closes his account (hard delete);
        # a backfill script fixes Mei's state but forgets to bump updated_at
        "UPDATE crm_src.customers SET plan = 'Premium', updated_at = '2025-01-03 08:00' WHERE customer_id = 1",
        "DELETE FROM crm_src.customers WHERE customer_id = 4",
        "UPDATE crm_src.customers SET state = 'NJ' WHERE customer_id = 3",
    ],
}


def apply_day(db_path: str, day: str) -> None:
    con = duckdb.connect(db_path)
    for stmt in DAYS[day]:
        con.execute(stmt)
    con.close()
