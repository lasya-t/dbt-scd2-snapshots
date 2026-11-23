-- every customer still in the source must have exactly one current version
select s.customer_id, count(h.customer_id) as current_rows
from {{ source('crm', 'customers') }} s
left join {{ ref('dim_customers_history') }} h
  on h.customer_id = s.customer_id and h.is_current
group by s.customer_id
having count(h.customer_id) != 1
