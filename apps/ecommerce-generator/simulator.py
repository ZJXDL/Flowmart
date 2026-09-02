import random
import time
from decimal import Decimal

import psycopg


DATABASE_URL = (
    "host=localhost "
    "port=5433 "
    "dbname=atlas "
    "user=atlas "
    "password=atlas_dev_password"
)


def load_data(connection):
    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT customer_id
            FROM customers
            """
        )

        customers = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT product_id, price
            FROM products
            """
        )

        products = cursor.fetchall()

    return customers, products


def create_order(connection, customers, products):

    with connection.cursor() as cursor:

        # Select a random customer
        customer_id = random.choice(customers)

        # Create the order
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
                "pending",
                Decimal("0.00"),
            ),
        )

        order_id = cursor.fetchone()[0]

        # Select 1–5 different products
        number_of_items = random.randint(1, 5)

        selected_products = random.sample(
            products,
            min(number_of_items, len(products)),
        )

        total_amount = Decimal("0.00")

        # Create order items
        for product_id, price in selected_products:

            quantity = random.randint(1, 4)

            unit_price = Decimal(str(price))

            total_amount += unit_price * quantity

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

            # Update inventory
            cursor.execute(
                """
                UPDATE inventory
                SET quantity = GREATEST(quantity - %s, 0),
                    updated_at = NOW()
                WHERE product_id = %s
                """,
                (
                    quantity,
                    product_id,
                ),
            )

        # Update final order total
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

        # Create payment
        payment_methods = [
            "credit_card",
            "debit_card",
            "paypal",
            "apple_pay",
            "google_pay",
        ]

        cursor.execute(
            """
            INSERT INTO payments (
                order_id,
                amount,
                status,
                payment_method
            )
            VALUES (%s, %s, %s, %s)
            RETURNING payment_id
            """,
            (
                order_id,
                total_amount,
                "completed",
                random.choice(payment_methods),
            ),
        )

        payment_id = cursor.fetchone()[0]

    # Commit the entire transaction
    connection.commit()

    return order_id, total_amount, payment_id


def main():

    print("Starting Atlas live simulator...")
    print("Press Ctrl+C to stop.")
    print()

    with psycopg.connect(DATABASE_URL) as connection:

        customers, products = load_data(connection)

        print(f"✓ Customers loaded: {len(customers)}")
        print(f"✓ Products loaded: {len(products)}")
        print()

        while True:

            try:

                order_id, total_amount, payment_id = create_order(
                    connection,
                    customers,
                    products,
                )

                print(
                    f"✓ Order {order_id} | "
                    f"Total: ${total_amount} | "
                    f"Payment: {payment_id}"
                )

                # Wait 3–7 seconds before the next transaction
                time.sleep(random.randint(3, 7))

            except KeyboardInterrupt:

                print()
                print("Stopping Atlas live simulator...")
                break

            except Exception as error:

                print(f"✗ Transaction failed: {error}")

                # Wait before trying again
                time.sleep(5)


if __name__ == "__main__":
    main()