-- a customer's versions must not overlap in time
select a.customer_id
from {{ ref('dim_customers_history') }} a
join {{ ref('dim_customers_history') }} b
  on a.customer_id = b.customer_id and a.customer_version_key < b.customer_version_key
where a.valid_from < coalesce(b.valid_to, timestamp '9999-12-31')
  and b.valid_from < coalesce(a.valid_to, timestamp '9999-12-31')
