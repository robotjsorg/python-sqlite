import argparse
import sqlite3
import sys
import os
from typing import Optional

#!/usr/bin/env python3
"""
Simple CLI tool to manage an artwork product inventory using SQLite.

Commands:
    init                Create DB and table (runs automatically on other commands).
    add                 Add a product.
    remove              Remove a product by id or sku.
    update-qty          Update product quantity (set or delta) by id or sku.
    list                List products (optionally filter by sku).
    get                 Show one product by id or sku.

Example:
    python test-sql.py add --title "Sunset" --artist "A. Painter" --year 2020 --price 150.0 --quantity 3 --sku SUN-001
    python test-sql.py update-qty --sku SUN-001 --delta -1
    python test-sql.py list
"""

DB_PATH = os.path.join(os.path.dirname(__file__), "artwork_inventory.db")
TABLE_SQL = """
CREATE TABLE IF NOT EXISTS artwork (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE,
        title TEXT NOT NULL,
        artist TEXT,
        year INTEGER,
        price REAL,
        quantity INTEGER NOT NULL DEFAULT 0
);
"""

def get_conn(path: str = DB_PATH):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

def init_db(conn):
        conn.execute(TABLE_SQL)
        conn.commit()

def add_product(conn, title: str, artist: Optional[str], year: Optional[int],
                                price: Optional[float], quantity: int, sku: Optional[str]):
        sql = "INSERT INTO artwork (sku, title, artist, year, price, quantity) VALUES (?, ?, ?, ?, ?, ?)"
        try:
                cur = conn.execute(sql, (sku, title, artist, year, price, quantity))
                conn.commit()
                print(f"Added product id={cur.lastrowid} title={title!r}")
        except sqlite3.IntegrityError as e:
                print("Error adding product:", e)

def remove_product(conn, id_: Optional[int], sku: Optional[str]):
        if id_ is None and sku is None:
                print("Provide --id or --sku to remove a product.")
                return
        if id_ is not None:
                cur = conn.execute("DELETE FROM artwork WHERE id = ?", (id_,))
        else:
                cur = conn.execute("DELETE FROM artwork WHERE sku = ?", (sku,))
        conn.commit()
        if cur.rowcount:
                print("Removed", cur.rowcount, "row(s).")
        else:
                print("No matching product found.")

def update_quantity(conn, id_: Optional[int], sku: Optional[str], set_qty: Optional[int], delta: Optional[int]):
        if id_ is None and sku is None:
                print("Provide --id or --sku to identify a product.")
                return
        if set_qty is None and delta is None:
                print("Provide --set or --delta to change quantity.")
                return

        if set_qty is not None:
                if id_ is not None:
                        cur = conn.execute("UPDATE artwork SET quantity = ? WHERE id = ?", (set_qty, id_))
                else:
                        cur = conn.execute("UPDATE artwork SET quantity = ? WHERE sku = ?", (set_qty, sku))
        else:
                # delta provided
                if id_ is not None:
                        cur = conn.execute("UPDATE artwork SET quantity = quantity + ? WHERE id = ?", (delta, id_))
                else:
                        cur = conn.execute("UPDATE artwork SET quantity = quantity + ? WHERE sku = ?", (delta, sku))
        conn.commit()
        if cur.rowcount:
                print("Updated quantity for", cur.rowcount, "row(s).")
        else:
                print("No matching product found.")

def list_products(conn, sku: Optional[str]):
        if sku:
                cur = conn.execute("SELECT * FROM artwork WHERE sku = ? ORDER BY id", (sku,))
        else:
                cur = conn.execute("SELECT * FROM artwork ORDER BY id")
        rows = cur.fetchall()
        if not rows:
                print("No products found.")
                return
        for r in rows:
                print(f"id={r['id']} sku={r['sku']!s} title={r['title']!r} artist={r['artist']!s} year={r['year']!s} price={r['price']!s} qty={r['quantity']}")

def get_product(conn, id_: Optional[int], sku: Optional[str]):
        if id_ is not None:
                cur = conn.execute("SELECT * FROM artwork WHERE id = ?", (id_,))
        elif sku is not None:
                cur = conn.execute("SELECT * FROM artwork WHERE sku = ?", (sku,))
        else:
                print("Provide --id or --sku to get a product.")
                return
        r = cur.fetchone()
        if not r:
                print("Product not found.")
                return
        print(dict(r))

def main(argv=None):
        parser = argparse.ArgumentParser(description="Artwork inventory CLI")
        sub = parser.add_subparsers(dest="cmd")
        # keep a mapping of subcommand name -> parser so we can show per-command help
        sub_parsers = {}

        sub_parsers['init'] = sub.add_parser("init", help="Create DB and table")

        p_add = sub.add_parser("add", help="Add a product")
        sub_parsers['add'] = p_add
        p_add.add_argument("--title", required=True)
        p_add.add_argument("--artist")
        p_add.add_argument("--year", type=int)
        p_add.add_argument("--price", type=float)
        p_add.add_argument("--quantity", type=int, default=0)
        p_add.add_argument("--sku")

        p_remove = sub.add_parser("remove", help="Remove a product by id or sku")
        sub_parsers['remove'] = p_remove
        p_remove.add_argument("--id", type=int)
        p_remove.add_argument("--sku")

        p_update = sub.add_parser("update-qty", help="Update product quantity (set or delta)")
        sub_parsers['update-qty'] = p_update
        p_update.add_argument("--id", type=int)
        p_update.add_argument("--sku")
        group = p_update.add_mutually_exclusive_group(required=True)
        group.add_argument("--set", dest="set_qty", type=int, help="Set absolute quantity")
        group.add_argument("--delta", type=int, help="Add/subtract from current quantity")

        p_list = sub.add_parser("list", help="List products")
        sub_parsers['list'] = p_list
        p_list.add_argument("--sku")

        p_get = sub.add_parser("get", help="Get one product")
        sub_parsers['get'] = p_get

        # provide a `help` subcommand to show help for specific commands: `help` or `help add`
        p_help = sub.add_parser("help", help="Show help for a command")
        p_help.add_argument("command", nargs="?", help="Command to show help for")
        sub_parsers['help'] = p_help
        p_get.add_argument("--id", type=int)
        p_get.add_argument("--sku")

        args = parser.parse_args(argv)

        conn = get_conn()
        init_db(conn)

        if args.cmd == "init":
                print("Database initialized.")
        elif args.cmd == "help":
                # `python test-sql.py help` -> show top-level help
                # `python test-sql.py help add` -> show help for the `add` subcommand
                cmd = getattr(args, 'command', None)
                if not cmd:
                        parser.print_help()
                else:
                        p = sub_parsers.get(cmd)
                        if p:
                                p.print_help()
                        else:
                                print(f"Unknown command: {cmd}")
        elif args.cmd == "add":
                add_product(conn, args.title, args.artist, args.year, args.price, args.quantity, args.sku)
        elif args.cmd == "remove":
                remove_product(conn, args.id, args.sku)
        elif args.cmd == "update-qty":
                update_quantity(conn, args.id, args.sku, args.set_qty, args.delta)
        elif args.cmd == "list":
                list_products(conn, args.sku)
        elif args.cmd == "get":
                get_product(conn, args.id, args.sku)
        else:
                parser.print_help()

if __name__ == "__main__":
        main()