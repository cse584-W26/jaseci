"""TPC-C benchmark - headless jac backend entry (LTI arm)."""

import from app { new_order, payment, get_district, get_customer, get_stock, get_item }
import from import_data {
    seed_items,
    seed_warehouse,
    seed_districts,
    seed_customers,
    seed_stock,
    seed_orders
}
