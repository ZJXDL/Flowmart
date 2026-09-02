import random
from decimal import Decimal

import psycopg


DATABASE_URL = (
    "host=localhost "
    "port=5433 "
    "dbname=atlas "
    "user=atlas "
    "password=atlas_dev_password"
)


# ---------------------------------------------------------
# STATIC DATA
# ---------------------------------------------------------

CATEGORIES = [
    ("Electronics", "Phones, computers, accessories and electronics"),
    ("Home & Kitchen", "Furniture, appliances and kitchen equipment"),
    ("Clothing", "Clothes, shoes and fashion accessories"),
    ("Sports", "Sports equipment and fitness products"),
    ("Books", "Books, novels and educational material"),
    ("Beauty", "Skincare, cosmetics and personal care"),
]


PRODUCTS = {
    "Electronics": [
        ("Wireless Headphones", 89.99),
        ("Mechanical Keyboard", 119.99),
        ("Gaming Mouse", 59.99),
        ("USB-C Hub", 39.99),
        ("Smartphone", 699.99),
        ("Laptop", 1299.99),
    ],
    "Home & Kitchen": [
        ("Coffee Maker", 149.99),
        ("Air Fryer", 99.99),
        ("Desk Lamp", 39.99),
        ("Blender", 79.99),
        ("Office Chair", 249.99),
    ],
    "Clothing": [
        ("Classic T-Shirt", 24.99),
        ("Running Shoes", 89.99),
        ("Denim Jacket", 79.99),
        ("Hoodie", 59.99),
        ("Sports Shorts", 34.99),
    ],
    "Sports": [
        ("Basketball", 29.99),
        ("Football", 34.99),
        ("Yoga Mat", 29.99),
        ("Dumbbell Set", 89.99),
        ("Running Watch", 149.99),
    ],
    "Books": [
        ("Python Programming", 49.99),
        ("Data Engineering Fundamentals", 59.99),
        ("The Art of Statistics", 44.99),
        ("Clean Code", 39.99),
        ("Machine Learning Guide", 69.99),
    ],
    "Beauty": [
        ("Face Cleanser", 19.99),
        ("Moisturizer", 29.99),
        ("Perfume", 89.99),
        ("Hair Dryer", 79.99),
        ("Skincare Set", 69.99),
    ],
}


FIRST_NAMES = [
    "Adam",
    "Omar",
    "Daniel",
    "Michael",
    "James",
    "David",
    "Alex",
    "Sarah",
    "Emma",
    "Sophia",
    "Liam",
    "Noah",
    "Maya",
    "Lina",
    "Yara",
    "Nour",
    "Layla",
    "Rami",
    "Karim",
    "Elias",
]


LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Davis",
    "Wilson",
    "Taylor",
    "Anderson",
    "Thomas",
    "Moore",
    "Haddad",
    "Khalil",
    "Mansour",
    "Saleh",
    "Nasser",
    "Khoury",
    "Saad",
    "Farah",
    "Rahme",
    "Issa",
]


LOCATIONS = [
    ("Lebanon", ["Beirut", "Tripoli", "Sidon", "Jounieh"]),
    ("United States", ["New York", "Chicago", "Los Angeles", "Boston"]),
    ("United Kingdom", ["London", "Manchester", "Birmingham"]),
    ("France", ["Paris", "Lyon", "Marseille"]),
    ("Germany", ["Berlin", "Munich", "Hamburg"]),
    ("Canada", ["Toronto", "Montreal", "Vancouver"]),
    ("Australia", ["Sydney", "Melbourne", "Brisbane"]),
    ("United Arab Emirates", ["Dubai", "Abu Dhabi", "Sharjah"]),
    ("Saudi Arabia", ["Riyadh", "Jeddah", "Dammam"]),
]


ORDER_STATUSES = [
    "completed",
    "completed",
    "completed",
    "completed",
    "completed",
    "completed",
    "completed",
    "shipped",
    "pending",
    "cancelled",
    "refunded",
]


PAYMENT_METHODS = [
    "credit_card",
    "debit_card",
    "paypal",
    "apple_pay",
    "google_pay",
]


# ---------------------------------------------------------
# CATEGORIES
# ---------------------------------------------------------

def generate_categories(connection):
    with connection.cursor() as cursor:

        for name, description in CATEGORIES:
            cursor.execute(
                """
                INSERT INTO categories (
                    name,
                    description
                )
                VALUES (%s, %s)
                ON CONFLICT (name)
                DO NOTHING
                """,
                (
                    name,
                    description,
                ),
            )

    connection.commit()

    print(f"✓ Categories ready: {len(CATEGORIES)}")


# ---------------------------------------------------------
# PRODUCTS
# ---------------------------------------------------------

def generate_products(connection):
    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT category_id, name
            FROM categories
            """
        )

        category_map = {
            name: category_id
            for category_id, name in cursor.fetchall()
        }

        product_count = 0

        for category_name, products in PRODUCTS.items():

            category_id = category_map[category_name]

            for product_name, price in products:

                # Use deterministic SKU based on category + product.
                sku = (
                    f"{category_name[:3].upper()}-"
                    f"{product_name[:3].upper()}"
                )

                cost = round(
                    price * random.uniform(0.45, 0.75),
                    2,
                )

                cursor.execute(
                    """
                    INSERT INTO products (
                        category_id,
                        sku,
                        name,
                        description,
                        price,
                        cost
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (sku)
                    DO NOTHING
                    """,
                    (
                        category_id,
                        sku,
                        product_name,
                        f"High-quality {product_name.lower()}",
                        Decimal(str(price)),
                        Decimal(str(cost)),
                    ),
                )

                product_count += 1

    connection.commit()

    print(f"✓ Products ready: {product_count}")


# ---------------------------------------------------------
# CUSTOMERS
# ---------------------------------------------------------

def generate_customers(connection, count=1000):
    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM customers
            """
        )

        existing_count = cursor.fetchone()[0]

        if existing_count >= count:
            print(f"✓ Customers already exist: {existing_count}")
            return

        customers_to_create = count - existing_count

        customer_count = 0

        for _ in range(customers_to_create):

            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)

            country, cities = random.choice(LOCATIONS)
            city = random.choice(cities)

            email = (
                f"{first_name.lower()}."
                f"{last_name.lower()}."
                f"{random.randint(10000, 99999)}"
                "@example.com"
            )

            cursor.execute(
                """
                INSERT INTO customers (
                    email,
                    first_name,
                    last_name,
                    country,
                    city
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email)
                DO NOTHING
                """,
                (
                    email,
                    first_name,
                    last_name,
                    country,
                    city,
                ),
            )

            customer_count += 1

    connection.commit()

    print(f"✓ Customers created: {customer_count}")


# ---------------------------------------------------------
# ORDERS
# ---------------------------------------------------------

def generate_orders(connection, count=5000):
    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM orders
            """
        )

        existing_count = cursor.fetchone()[0]

        if existing_count >= count:
            print(f"✓ Orders already exist: {existing_count}")
            return

        orders_to_create = count - existing_count

        cursor.execute(
            """
            SELECT customer_id
            FROM customers
            """
        )

        customer_ids = [
            row[0]
            for row in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT product_id, price
            FROM products
            """
        )

        products = cursor.fetchall()

        order_count = 0
        item_count = 0

        for _ in range(orders_to_create):

            customer_id = random.choice(customer_ids)

            status = random.choice(
                ORDER_STATUSES
            )

            cursor.execute(
                """
                INSERT INTO orders (
                    customer_id,
                    status,
                    total_amount
                )
                VALUES (%s, %s, %s)
                RETURNING order_id
                """,
                (
                    customer_id,
                    status,
                    Decimal("0.00"),
                ),
            )

            order_id = cursor.fetchone()[0]

            number_of_items = random.randint(1, 5)

            selected_products = random.sample(
                products,
                min(
                    number_of_items,
                    len(products),
                ),
            )

            total_amount = Decimal("0.00")

            for product_id, price in selected_products:

                quantity = random.randint(1, 4)

                unit_price = Decimal(str(price))

                total_amount += (
                    unit_price * quantity
                )

                cursor.execute(
                    """
                    INSERT INTO order_items (
                        order_id,
                        product_id,
                        quantity,
                        unit_price
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        order_id,
                        product_id,
                        quantity,
                        unit_price,
                    ),
                )

                item_count += 1

            cursor.execute(
                """
                UPDATE orders
                SET total_amount = %s,
                    updated_at = NOW()
                WHERE order_id = %s
                """,
                (
                    total_amount,
                    order_id,
                ),
            )

            order_count += 1

    connection.commit()

    print(f"✓ Orders created: {order_count}")
    print(f"✓ Order items created: {item_count}")


# ---------------------------------------------------------
# PAYMENTS
# ---------------------------------------------------------

def generate_payments(connection):
    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT
                o.order_id,
                o.total_amount,
                o.status
            FROM orders o
            LEFT JOIN payments p
                ON p.order_id = o.order_id
            WHERE p.payment_id IS NULL
            """
        )

        orders_without_payments = cursor.fetchall()

        payment_count = 0

        for order_id, total_amount, order_status in orders_without_payments:

            if order_status == "cancelled":
                payment_status = "failed"

            elif order_status == "refunded":
                payment_status = "refunded"

            elif order_status == "pending":
                payment_status = "pending"

            else:
                payment_status = "completed"

            payment_method = random.choice(
                PAYMENT_METHODS
            )

            cursor.execute(
                """
                INSERT INTO payments (
                    order_id,
                    amount,
                    status,
                    payment_method
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    order_id,
                    total_amount,
                    payment_status,
                    payment_method,
                ),
            )

            payment_count += 1

    connection.commit()

    print(f"✓ Payments created: {payment_count}")


# ---------------------------------------------------------
# INVENTORY
# ---------------------------------------------------------

def generate_inventory(connection):
    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT
                p.product_id
            FROM products p
            LEFT JOIN inventory i
                ON i.product_id = p.product_id
            WHERE i.inventory_id IS NULL
            """
        )

        products_without_inventory = cursor.fetchall()

        inventory_count = 0

        for (product_id,) in products_without_inventory:

            quantity = random.randint(10, 500)

            cursor.execute(
                """
                INSERT INTO inventory (
                    product_id,
                    quantity
                )
                VALUES (%s, %s)
                """,
                (
                    product_id,
                    quantity,
                ),
            )

            inventory_count += 1

    connection.commit()

    print(f"✓ Inventory records created: {inventory_count}")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("Starting Atlas data generator...")
    print()

    with psycopg.connect(DATABASE_URL) as connection:

        generate_categories(connection)

        generate_products(connection)

        generate_customers(connection)

        generate_orders(connection)

        generate_payments(connection)

        generate_inventory(connection)

    print()
    print("✓ Atlas initial data generation complete.")

if __name__ == "__main__":
    main()