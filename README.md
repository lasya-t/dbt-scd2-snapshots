# SCD Type 2 with dbt Snapshots

The CRM database only stores each customer's **current** row: when a plan changes, the old value is overwritten, and when an account closes, the row is deleted. This project uses dbt snapshots to keep the full history, so questions like *"what plan was this customer on last March?"* can still be answered.

It compares dbt's two snapshot strategies on the same three days of changes, including one change each strategy handles differently.

## Setup

`source_system.py` plays the app database (`crm_src.customers` in DuckDB). `run_days.py` applies one day of changes, runs `dbt snapshot`, and repeats:

| Day | What the app does |
|---|---|
| Jan 1 | 4 customers created |
| Jan 2 | Ana upgrades Basic → Unlimited, Raj moves NJ → PA, Lena signs up |
| Jan 3 | Ana upgrades again → Premium, Omar's account is **deleted**, and a backfill script fixes Mei's state **without updating `updated_at`** |

## Results

**Timestamp strategy** (trusts `updated_at`): 8 versions.
```
 customer_id name state      plan  valid_from    valid_to
           1  Ana    PA     Basic 01-01 09:00 01-02 10:15
           1  Ana    PA Unlimited 01-02 10:15 01-03 08:00
           1  Ana    PA   Premium 01-03 08:00     current
           3  Mei    NY     Basic 01-01 09:00     current     <- missed the NY -> NJ fix
           4 Omar    DE   Premium 01-01 09:00  (closed)       <- delete recorded, row kept
```

**Check strategy** (compares `name, state, plan` directly): 9 versions, including `Mei NY → NJ`.

| | Timestamp | Check |
|---|---|---|
| Catches changes made without touching `updated_at` | ✗ | ✓ |
| `valid_from` reflects when the change actually happened | ✓ (source time) | ✗ (time the snapshot ran) |
| Cost | cheap: compares one column | compares every tracked column on every run |

**Rule of thumb:** use `timestamp` when the source reliably maintains `updated_at`, and `check` (or both) when backfills and scripts edit rows directly.

`hard_deletes: invalidate` closes the deleted customer's last version instead of leaving it looking current. Without it, Omar would appear active forever.

## The history dimension

`dim_customers_history` puts a clean SCD2 interface on the snapshot: `valid_from`, `valid_to`, `is_current`, `version`. An as-of query for Jan 2 at noon returns Ana on **Unlimited**, the plan she had at that moment.

Data tests run on every build:
- every customer still in the source has exactly one current version
- a customer's versions never overlap in time
- version keys are unique

## How to run

```bash
pip install -r requirements.txt
export DBT_PROFILES_DIR=.
python run_days.py      # replays 3 days, prints both histories and the as-of query
pytest
```

## Next steps
- Join the history dimension to orders, so each order picks up the plan that was current at order time
- Snapshot from a CDC stream instead of daily polling
