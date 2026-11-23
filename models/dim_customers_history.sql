-- SCD2 dimension built on the timestamp snapshot: one row per version of a customer
select
    dbt_scd_id                      as customer_version_key,
    customer_id,
    name,
    state,
    plan,
    dbt_valid_from                  as valid_from,
    dbt_valid_to                    as valid_to,
    dbt_valid_to is null            as is_current,
    row_number() over (partition by customer_id order by dbt_valid_from) as version
from {{ ref('customers_snapshot_ts') }}
