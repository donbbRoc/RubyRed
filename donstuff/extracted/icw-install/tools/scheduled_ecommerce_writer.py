#!/usr/bin/env python3
"""
Scheduled writer that appends data to the 10 ecommerce files in /opt/documents every 1 hour.

Distribution:
  10,000 rows: product_catalog.csv, customer_orders.csv, order_line_items.csv
     100 rows: shopping_cart_snapshot.csv, shipping_fulfillment.csv, customer_reviews.csv
       1 row:  inventory_movements.csv, discount_coupons.csv, refund_requests.csv, vendor_suppliers.csv

Usage: python3 scheduled_ecommerce_writer.py
"""

import os
import csv
import random
import string
import sys
import time
from datetime import datetime, timedelta

OUTPUT_DIR = "/opt/documents"
INTERVAL_SECONDS = 3600  # 1 hour


def rs(n):
    return ''.join(random.choices(string.ascii_letters, k=n))

def rand_date(y1=2024, y2=2026):
    start = datetime(y1, 1, 1)
    days = (datetime(y2, 12, 31) - start).days
    return (start + timedelta(days=random.randint(0, days))).strftime('%Y-%m-%d')

def rand_dec(lo, hi):
    return round(random.uniform(lo, hi), 2)

def rand_phone():
    return f"{random.randint(100,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}"


def append_csv(filepath, headers, gen_row, count):
    """Append rows to an existing CSV. Writes header if file is empty or missing."""
    write_header = not os.path.exists(filepath) or os.path.getsize(filepath) == 0
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(headers)
        for i in range(count):
            writer.writerow(gen_row(i))
    print(f"  [OK] {os.path.basename(filepath)}: {count} rows appended")


def run_writes():
    """Single execution: append data to all 10 files."""
    run_ts = datetime.now().strftime('%m%d%H%M%S')
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] Starting write cycle (run_id={run_ts})...\n")

    # --- 10,000 rows: 3 files ---

    print("  -- 10,000 rows each --")

    append_csv(
        os.path.join(OUTPUT_DIR, "product_catalog.csv"),
        ["product_id", "product_name", "category", "price", "stock_qty", "sku"],
        lambda i: [f"PROD-{run_ts}-{i+1:05d}", f"{rs(8)} {rs(5)}",
                   random.choice(["Electronics", "Clothing", "Home", "Sports", "Beauty"]),
                   rand_dec(5, 999), random.randint(0, 5000), f"SKU-{rs(6).upper()}"],
        10000
    )

    append_csv(
        os.path.join(OUTPUT_DIR, "customer_orders.csv"),
        ["order_id", "customer_email", "order_date", "total_amount", "status", "payment_method"],
        lambda i: [f"ORD-{run_ts}-{i+1:06d}", f"{rs(6).lower()}@{rs(4).lower()}.com", rand_date(),
                   rand_dec(10, 2500), random.choice(["Pending", "Shipped", "Delivered", "Cancelled", "Returned"]),
                   random.choice(["Credit Card", "PayPal", "Apple Pay", "Debit Card"])],
        10000
    )

    append_csv(
        os.path.join(OUTPUT_DIR, "order_line_items.csv"),
        ["line_id", "order_id", "product_id", "quantity", "unit_price", "discount_pct"],
        lambda i: [f"LN-{run_ts}-{i+1:06d}", f"ORD-{run_ts}-{random.randint(1,10000):06d}",
                   f"PROD-{run_ts}-{random.randint(1,10000):05d}",
                   random.randint(1, 10), rand_dec(5, 500), random.choice([0, 5, 10, 15, 20])],
        10000
    )

    # --- 100 rows: 3 files ---

    print("  -- 100 rows each --")

    append_csv(
        os.path.join(OUTPUT_DIR, "shopping_cart_snapshot.csv"),
        ["cart_id", "customer_email", "product_id", "quantity", "added_date", "cart_status"],
        lambda i: [f"CART-{run_ts}-{i+1:05d}", f"{rs(6).lower()}@{rs(4).lower()}.com",
                   f"PROD-{run_ts}-{random.randint(1,10000):05d}",
                   random.randint(1, 5), rand_date(), random.choice(["Active", "Abandoned", "Converted"])],
        100
    )

    append_csv(
        os.path.join(OUTPUT_DIR, "shipping_fulfillment.csv"),
        ["shipment_id", "order_id", "carrier", "tracking_number", "ship_date", "delivery_date", "status"],
        lambda i: [f"SHP-{run_ts}-{i+1:06d}", f"ORD-{run_ts}-{random.randint(1,10000):06d}",
                   random.choice(["FedEx", "UPS", "USPS", "DHL"]),
                   f"TRK{random.randint(1000000000,9999999999)}", rand_date(),
                   rand_date(2025, 2026), random.choice(["In Transit", "Delivered", "Out for Delivery", "Exception"])],
        100
    )

    append_csv(
        os.path.join(OUTPUT_DIR, "customer_reviews.csv"),
        ["review_id", "product_id", "customer_email", "rating", "title", "review_date"],
        lambda i: [f"REV-{run_ts}-{i+1:05d}", f"PROD-{run_ts}-{random.randint(1,10000):05d}",
                   f"{rs(6).lower()}@{rs(4).lower()}.com",
                   random.randint(1, 5), f"{rs(10)} {rs(8)}", rand_date()],
        100
    )

    # --- 1 row: 4 files ---

    print("  -- 1 row each --")

    append_csv(
        os.path.join(OUTPUT_DIR, "inventory_movements.csv"),
        ["movement_id", "product_id", "warehouse", "movement_type", "quantity", "movement_date"],
        lambda i: [f"INV-{run_ts}-{i+1:06d}", f"PROD-{run_ts}-{random.randint(1,10000):05d}",
                   random.choice(["Warehouse-A", "Warehouse-B", "Warehouse-C"]),
                   random.choice(["Inbound", "Outbound", "Adjustment", "Return"]),
                   random.randint(1, 500), rand_date()],
        1
    )

    append_csv(
        os.path.join(OUTPUT_DIR, "discount_coupons.csv"),
        ["coupon_code", "discount_type", "discount_value", "min_order", "valid_from", "valid_until", "usage_count"],
        lambda i: [f"{rs(4).upper()}{run_ts}", random.choice(["Percentage", "Fixed"]),
                   random.choice([5, 10, 15, 20, 25, 50]), rand_dec(20, 200),
                   rand_date(2025, 2025), rand_date(2026, 2026), random.randint(0, 1000)],
        1
    )

    append_csv(
        os.path.join(OUTPUT_DIR, "refund_requests.csv"),
        ["refund_id", "order_id", "reason", "refund_amount", "request_date", "status"],
        lambda i: [f"RFD-{run_ts}-{i+1:05d}", f"ORD-{run_ts}-{random.randint(1,10000):06d}",
                   random.choice(["Damaged", "Wrong Item", "Not as Described", "Late Delivery", "Changed Mind"]),
                   rand_dec(10, 500), rand_date(), random.choice(["Pending", "Approved", "Rejected", "Processed"])],
        1
    )

    append_csv(
        os.path.join(OUTPUT_DIR, "vendor_suppliers.csv"),
        ["vendor_id", "vendor_name", "contact_email", "phone", "country", "product_categories", "rating"],
        lambda i: [f"VND-{run_ts}-{i+1:04d}", f"{rs(8)} {random.choice(['LLC', 'Inc', 'Corp', 'Ltd'])}",
                   f"contact@{rs(6).lower()}.com", rand_phone(),
                   random.choice(["US", "CN", "IN", "DE", "JP", "UK"]),
                   random.choice(["Electronics", "Clothing", "Home", "Sports", "Beauty"]),
                   round(random.uniform(3.0, 5.0), 1)],
        1
    )

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Write cycle complete.")


def main():
    print(f"Scheduler started. Will write to ecommerce files every {INTERVAL_SECONDS // 60} minutes.")
    print(f"Output directory: {OUTPUT_DIR}")
    print("Press Ctrl+C to stop.\n")

    run_count = 0
    while True:
        run_count += 1
        print(f"{'=' * 60}")
        print(f"Run #{run_count}")
        print(f"{'=' * 60}")

        run_writes()

        print(f"\nNext run in {INTERVAL_SECONDS // 60} minutes (sleeping)...")

        try:
            time.sleep(INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print(f"\nScheduler stopped after {run_count} run(s).")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScheduler stopped.")
        sys.exit(0)
