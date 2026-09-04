#!/usr/bin/env python3
"""
Creates 10 sample ecommerce data files inside /opt/documents.
Usage: python3 create_ecommerce_files.py
"""

import os
import csv
import random
import string
from datetime import datetime, timedelta

OUTPUT_DIR = "/opt/documents"


def rs(n):
    return ''.join(random.choices(string.ascii_letters, k=n))

def rand_date(y1=2024, y2=2026):
    start = datetime(y1, 1, 1)
    days = (datetime(y2, 12, 31) - start).days
    return (start + timedelta(days=random.randint(0, days))).strftime('%Y-%m-%d')

def rand_dec(lo, hi):
    return round(random.uniform(lo, hi), 2)


def write_csv(filepath, headers, gen_row, count):
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for i in range(count):
            writer.writerow(gen_row(i))
    print(f"  [OK] {filepath} ({count} rows)")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Creating 10 ecommerce files in {OUTPUT_DIR}\n")

    # 1. Product catalog
    write_csv(
        os.path.join(OUTPUT_DIR, "product_catalog.csv"),
        ["product_id", "product_name", "category", "price", "stock_qty", "sku"],
        lambda i: [f"PROD-{i+1:05d}", f"{rs(8)} {rs(5)}", random.choice(["Electronics", "Clothing", "Home", "Sports", "Beauty"]),
                   rand_dec(5, 999), random.randint(0, 5000), f"SKU-{rs(6).upper()}"],
        50
    )

    # 2. Customer orders
    write_csv(
        os.path.join(OUTPUT_DIR, "customer_orders.csv"),
        ["order_id", "customer_email", "order_date", "total_amount", "status", "payment_method"],
        lambda i: [f"ORD-{i+1:06d}", f"{rs(6).lower()}@{rs(4).lower()}.com", rand_date(),
                   rand_dec(10, 2500), random.choice(["Pending", "Shipped", "Delivered", "Cancelled", "Returned"]),
                   random.choice(["Credit Card", "PayPal", "Apple Pay", "Debit Card"])],
        100
    )

    # 3. Order line items
    write_csv(
        os.path.join(OUTPUT_DIR, "order_line_items.csv"),
        ["line_id", "order_id", "product_id", "quantity", "unit_price", "discount_pct"],
        lambda i: [f"LN-{i+1:06d}", f"ORD-{random.randint(1,100):06d}", f"PROD-{random.randint(1,50):05d}",
                   random.randint(1, 10), rand_dec(5, 500), random.choice([0, 5, 10, 15, 20])],
        200
    )

    # 4. Shopping cart snapshots
    write_csv(
        os.path.join(OUTPUT_DIR, "shopping_cart_snapshot.csv"),
        ["cart_id", "customer_email", "product_id", "quantity", "added_date", "cart_status"],
        lambda i: [f"CART-{i+1:05d}", f"{rs(6).lower()}@{rs(4).lower()}.com", f"PROD-{random.randint(1,50):05d}",
                   random.randint(1, 5), rand_date(), random.choice(["Active", "Abandoned", "Converted"])],
        80
    )

    # 5. Shipping and fulfillment
    write_csv(
        os.path.join(OUTPUT_DIR, "shipping_fulfillment.csv"),
        ["shipment_id", "order_id", "carrier", "tracking_number", "ship_date", "delivery_date", "status"],
        lambda i: [f"SHP-{i+1:06d}", f"ORD-{random.randint(1,100):06d}",
                   random.choice(["FedEx", "UPS", "USPS", "DHL"]),
                   f"TRK{random.randint(1000000000,9999999999)}", rand_date(),
                   rand_date(2025, 2026), random.choice(["In Transit", "Delivered", "Out for Delivery", "Exception"])],
        100
    )

    # 6. Customer reviews
    write_csv(
        os.path.join(OUTPUT_DIR, "customer_reviews.csv"),
        ["review_id", "product_id", "customer_email", "rating", "title", "review_date"],
        lambda i: [f"REV-{i+1:05d}", f"PROD-{random.randint(1,50):05d}", f"{rs(6).lower()}@{rs(4).lower()}.com",
                   random.randint(1, 5), f"{rs(10)} {rs(8)}", rand_date()],
        60
    )

    # 7. Inventory movements
    write_csv(
        os.path.join(OUTPUT_DIR, "inventory_movements.csv"),
        ["movement_id", "product_id", "warehouse", "movement_type", "quantity", "movement_date"],
        lambda i: [f"INV-{i+1:06d}", f"PROD-{random.randint(1,50):05d}",
                   random.choice(["Warehouse-A", "Warehouse-B", "Warehouse-C"]),
                   random.choice(["Inbound", "Outbound", "Adjustment", "Return"]),
                   random.randint(1, 500), rand_date()],
        150
    )

    # 8. Discount coupons
    write_csv(
        os.path.join(OUTPUT_DIR, "discount_coupons.csv"),
        ["coupon_code", "discount_type", "discount_value", "min_order", "valid_from", "valid_until", "usage_count"],
        lambda i: [f"{rs(4).upper()}{random.randint(10,99)}", random.choice(["Percentage", "Fixed"]),
                   random.choice([5, 10, 15, 20, 25, 50]), rand_dec(20, 200),
                   rand_date(2025, 2025), rand_date(2026, 2026), random.randint(0, 1000)],
        30
    )

    # 9. Refund requests
    write_csv(
        os.path.join(OUTPUT_DIR, "refund_requests.csv"),
        ["refund_id", "order_id", "reason", "refund_amount", "request_date", "status"],
        lambda i: [f"RFD-{i+1:05d}", f"ORD-{random.randint(1,100):06d}",
                   random.choice(["Damaged", "Wrong Item", "Not as Described", "Late Delivery", "Changed Mind"]),
                   rand_dec(10, 500), rand_date(), random.choice(["Pending", "Approved", "Rejected", "Processed"])],
        40
    )

    # 10. Vendor suppliers
    write_csv(
        os.path.join(OUTPUT_DIR, "vendor_suppliers.csv"),
        ["vendor_id", "vendor_name", "contact_email", "phone", "country", "product_categories", "rating"],
        lambda i: [f"VND-{i+1:04d}", f"{rs(8)} {random.choice(['LLC', 'Inc', 'Corp', 'Ltd'])}",
                   f"contact@{rs(6).lower()}.com", f"{random.randint(100,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}",
                   random.choice(["US", "CN", "IN", "DE", "JP", "UK"]),
                   random.choice(["Electronics", "Clothing", "Home", "Sports", "Beauty"]),
                   round(random.uniform(3.0, 5.0), 1)],
        20
    )

    print(f"\nDone. 10 ecommerce files created in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
