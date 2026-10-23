"""
Administrative CLI script to securely create or reset administrator credentials
without exposing passwords in the frontend or public configuration.

Usage:
    Interactive (recommended):
        python create_admin.py

    With arguments:
        python create_admin.py --username admin --password MySecurePassword123
"""

import sys
import getpass
import argparse
from config import Config
from database import _execute_init, connect_db
from auth import create_admin_account


def main():
    parser = argparse.ArgumentParser(description="Create a new administrator account for Emoji Team Generator.")
    parser.add_argument("--username", "-u", help="Administrator username")
    parser.add_argument("--password", "-p", help="Administrator password (min 6 characters)")
    args = parser.parse_args()

    username = args.username
    password = args.password

    if not username:
        username = input("Enter administrator username: ").strip()

    if not username:
        print("Error: Username cannot be empty.")
        sys.exit(1)

    if not password:
        password = getpass.getpass("Enter administrator password: ")
        password_confirm = getpass.getpass("Confirm administrator password: ")
        if password != password_confirm:
            print("Error: Passwords do not match.")
            sys.exit(1)

    if len(password) < 6:
        print("Error: Password must be at least 6 characters long.")
        sys.exit(1)

    # Initialize tables if needed
    _execute_init(Config.DATABASE_PATH)

    conn = connect_db(Config.DATABASE_PATH)
    try:
        success = create_admin_account(username, password, conn=conn)
        if success:
            print(f"Success: Administrator account '{username}' created successfully.")
        else:
            print(f"Error: An administrator with username '{username}' already exists.")
            sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
