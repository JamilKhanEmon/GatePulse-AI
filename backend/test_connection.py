#!/usr/bin/env python3
"""Diagnostic utility to test database connectivity"""

import os
import sys

# Ensure local modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import env_loader
except ImportError:
    pass

try:
    import mysql.connector
except ImportError:
    print("Error: mysql-connector-python is not installed. Run 'pip install mysql-connector-python'.")
    sys.exit(1)

def test_connection(host, user, password, port=3306, database=None):
    try:
        config = {
            'host': host,
            'user': user,
            'password': password,
            'port': int(port)
        }
        if database:
            config['database'] = database

        conn = mysql.connector.connect(**config)
        conn.close()
        return True, "Connection established successfully"
    except Exception as e:
        return False, str(e)

def main():
    print("Testing MySQL connection from environment configuration...")

    env_host = os.environ.get('DB_HOST', 'localhost')
    env_port = int(os.environ.get('DB_PORT', 3306))
    env_user = os.environ.get('DB_USER', 'root')
    env_pass = os.environ.get('DB_PASSWORD', '')
    env_name = os.environ.get('DB_NAME', 'gatepulse_db')

    print(f"Target: {env_user}@{env_host}:{env_port} (Database: {env_name})")

    # Primary check: credentials from environment
    ok, msg = test_connection(env_host, env_user, env_pass, env_port)
    if ok:
        print("  -> Base MySQL connection succeeded.")
        db_ok, db_msg = test_connection(env_host, env_user, env_pass, env_port, env_name)
        if db_ok:
            print(f"  -> Successfully connected to '{env_name}' database.")
            return
        else:
            print(f"  -> Database '{env_name}' not reachable yet: {db_msg}")
            print("     You can create it by running schema.sql or starting the app.")
            return
    else:
        print(f"  -> Primary connection failed: {msg}")

    # Fallback checks with common local configurations
    print("\nAttempting common local development fallbacks...")
    fallbacks = [
        {"host": "localhost", "user": "root", "password": "", "port": 3306},
        {"host": "127.0.0.1", "user": "root", "password": "", "port": 3306},
    ]

    for fb in fallbacks:
        fb_ok, _ = test_connection(fb['host'], fb['user'], fb['password'], fb['port'])
        if fb_ok:
            print(f"  -> Found working connection with {fb['user']}@{fb['host']}:{fb['port']} with empty password.")
            print("     Update your .env file with these values.")
            return

    print("\nTroubleshooting tips:")
    print("1. Ensure MySQL server is running (e.g. 'brew services status mysql' or 'systemctl status mysql').")
    print("2. Verify credentials in your .env file.")

if __name__ == '__main__':
    main()
