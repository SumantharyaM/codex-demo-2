"""Command-line user management for the GrandPal MySQL database.

Examples:
    python manage_users.py list
    python manage_users.py add --name "Asha Patel" --email asha@example.com --phone 5551234567 --city Pune
    python manage_users.py delete --email asha@example.com
    python manage_users.py update --email asha@example.com --phone 5557654321
"""

import argparse
import sys

import mysql.connector
from mysql.connector import Error

from app import DATABASE_CONFIG


def get_connection():
    """Create a fresh connection using the same settings as the Flask app."""
    if not DATABASE_CONFIG["password"]:
        print("Error: MYSQL_PASSWORD is not configured.")
        return None

    try:
        return mysql.connector.connect(**DATABASE_CONFIG)
    except Error as error:
        print(f"Error: Could not connect to the GrandPal database. {error}")
        return None


def value_or_prompt(value, label):
    """Use a provided command option or ask for the value interactively."""
    if value:
        return value.strip()
    return input(f"{label}: ").strip()


def list_users(connection):
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT name, email, phone, city FROM users ORDER BY name")
        users = cursor.fetchall()

        if not users:
            print("No users found.")
            return

        print(f"{'Name':<25} {'Email':<32} {'Phone':<18} City")
        print("-" * 90)
        for name, email, phone, city in users:
            print(f"{name:<25} {email:<32} {phone:<18} {city}")
        print(f"\nSuccess: Listed {len(users)} user(s).")
    except Error as error:
        print(f"Error: Could not list users. {error}")
    finally:
        if cursor:
            cursor.close()


def add_user(connection, args):
    name = value_or_prompt(args.name, "Name")
    email = value_or_prompt(args.email, "Email")
    phone = value_or_prompt(args.phone, "Phone number")
    city = value_or_prompt(args.city, "City")

    if not all((name, email, phone, city)):
        print("Error: Name, email, phone number, and city are all required.")
        return

    cursor = None
    try:
        cursor = connection.cursor(prepared=True)
        cursor.execute(
            "INSERT INTO users (name, email, phone, city) VALUES (%s, %s, %s, %s)",
            (name, email, phone, city),
        )
        connection.commit()
        print(f"Success: Added {name} ({email}).")
    except Error as error:
        connection.rollback()
        print(f"Error: Could not add user. {error}")
    finally:
        if cursor:
            cursor.close()


def delete_user(connection, args):
    email = value_or_prompt(args.email, "Email to delete")
    if not email:
        print("Error: Email is required.")
        return

    cursor = None
    try:
        cursor = connection.cursor(prepared=True)
        cursor.execute("DELETE FROM users WHERE email = %s", (email,))
        connection.commit()
        if cursor.rowcount:
            print(f"Success: Deleted user with email {email}.")
        else:
            print(f"Error: No user found with email {email}.")
    except Error as error:
        connection.rollback()
        print(f"Error: Could not delete user. {error}")
    finally:
        if cursor:
            cursor.close()


def update_user(connection, args):
    email = value_or_prompt(args.email, "Email of user to update")
    phone = args.phone
    city = args.city

    if not phone and not city:
        print("Leave a value blank to keep it unchanged.")
        phone = input("New phone number: ").strip() or None
        city = input("New city: ").strip() or None

    if not email:
        print("Error: Email is required.")
        return
    if not phone and not city:
        print("Error: Provide a new phone number or city.")
        return

    assignments = []
    values = []
    if phone:
        assignments.append("phone = %s")
        values.append(phone.strip())
    if city:
        assignments.append("city = %s")
        values.append(city.strip())
    values.append(email)

    cursor = None
    try:
        cursor = connection.cursor(prepared=True)
        cursor.execute(
            f"UPDATE users SET {', '.join(assignments)} WHERE email = %s", tuple(values)
        )
        connection.commit()
        if cursor.rowcount:
            print(f"Success: Updated user with email {email}.")
        else:
            print(f"Error: No user found with email {email}.")
    except Error as error:
        connection.rollback()
        print(f"Error: Could not update user. {error}")
    finally:
        if cursor:
            cursor.close()


def parse_arguments():
    parser = argparse.ArgumentParser(description="Manage GrandPal users in MySQL.")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="Show all users.")

    add_parser = commands.add_parser("add", help="Add a new user.")
    add_parser.add_argument("--name")
    add_parser.add_argument("--email")
    add_parser.add_argument("--phone")
    add_parser.add_argument("--city")

    delete_parser = commands.add_parser("delete", help="Delete a user by email.")
    delete_parser.add_argument("--email")

    update_parser = commands.add_parser("update", help="Update a user's phone or city by email.")
    update_parser.add_argument("--email")
    update_parser.add_argument("--phone")
    update_parser.add_argument("--city")
    return parser.parse_args()


def main():
    args = parse_arguments()
    connection = get_connection()
    if not connection:
        return 1

    try:
        if args.command == "list":
            list_users(connection)
        elif args.command == "add":
            add_user(connection, args)
        elif args.command == "delete":
            delete_user(connection, args)
        elif args.command == "update":
            update_user(connection, args)
    except (EOFError, KeyboardInterrupt):
        print("\nError: Command cancelled.")
        return 1
    finally:
        if connection.is_connected():
            connection.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
