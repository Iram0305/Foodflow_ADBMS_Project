import threading
import time

import psycopg2

from core import database

MODES = {
    "No locking (unsafe)": "none",
    "Pessimistic locking (SELECT ... FOR UPDATE)": "pessimistic",
    "Optimistic locking (version column)": "optimistic",
    "SERIALIZABLE isolation": "serializable",
}


class Timeline:
    def __init__(self):
        self.start = time.perf_counter()
        self.lock = threading.Lock()
        self.events = []

    def add(self, who, action, sql=""):
        moment = round((time.perf_counter() - self.start) * 1000)
        with self.lock:
            self.events.append({"ms": moment, "customer": who, "action": action, "sql": sql})


def buyer(who, mode, item_id, timeline, results, barrier, head_start, think_time):
    connection = database.connect(autocommit=True)
    cursor = connection.cursor()
    sold = False
    try:
        barrier.wait()
        time.sleep(head_start)
        if mode == "serializable":
            cursor.execute("BEGIN ISOLATION LEVEL SERIALIZABLE")
            timeline.add(who, "BEGIN (SERIALIZABLE)", "BEGIN ISOLATION LEVEL SERIALIZABLE;")
        else:
            cursor.execute("BEGIN")
            timeline.add(who, "BEGIN", "BEGIN;")

        if mode == "pessimistic":
            timeline.add(who, "Asking for row lock...", "SELECT stock FROM menu_item WHERE item_id = " + str(item_id) + " FOR UPDATE;")
            cursor.execute("SELECT stock, version FROM menu_item WHERE item_id = %s FOR UPDATE", (item_id,))
            stock, version = cursor.fetchone()
            timeline.add(who, "Got the lock, sees stock = " + str(stock))
        else:
            cursor.execute("SELECT stock, version FROM menu_item WHERE item_id = %s", (item_id,))
            stock, version = cursor.fetchone()
            timeline.add(who, "Reads stock = " + str(stock) + " (version " + str(version) + ")", "SELECT stock, version FROM menu_item WHERE item_id = " + str(item_id) + ";")

        timeline.add(who, "Customer is paying...")
        time.sleep(think_time)

        if stock < 1:
            cursor.execute("ROLLBACK")
            timeline.add(who, "Out of stock, order rejected", "ROLLBACK;")
            results[who] = "REJECTED"
            return

        if mode == "none":
            cursor.execute("UPDATE menu_item SET stock = %s WHERE item_id = %s", (stock - 1, item_id))
            timeline.add(who, "Writes stock = " + str(stock - 1), "UPDATE menu_item SET stock = " + str(stock - 1) + " WHERE item_id = " + str(item_id) + ";")
            sold = True
        elif mode == "pessimistic":
            cursor.execute("UPDATE menu_item SET stock = stock - 1 WHERE item_id = %s", (item_id,))
            timeline.add(who, "Reduces stock by 1", "UPDATE menu_item SET stock = stock - 1 WHERE item_id = " + str(item_id) + ";")
            sold = True
        elif mode == "optimistic":
            cursor.execute("UPDATE menu_item SET stock = stock - 1, version = version + 1 WHERE item_id = %s AND version = %s", (item_id, version))
            sql = "UPDATE menu_item SET stock = stock - 1, version = version + 1\nWHERE item_id = " + str(item_id) + " AND version = " + str(version) + ";"
            if cursor.rowcount == 0:
                timeline.add(who, "0 rows updated: version changed, someone else bought it", sql)
                cursor.execute("ROLLBACK")
                timeline.add(who, "Conflict detected, order rejected", "ROLLBACK;")
                results[who] = "REJECTED"
                return
            timeline.add(who, "1 row updated, version " + str(version) + " -> " + str(version + 1), sql)
            sold = True
        elif mode == "serializable":
            try:
                cursor.execute("UPDATE menu_item SET stock = stock - 1 WHERE item_id = %s", (item_id,))
                timeline.add(who, "Reduces stock by 1", "UPDATE menu_item SET stock = stock - 1 WHERE item_id = " + str(item_id) + ";")
                sold = True
            except psycopg2.Error as error:
                timeline.add(who, "ERROR: " + str(error).splitlines()[0])
                cursor.execute("ROLLBACK")
                timeline.add(who, "Transaction aborted, order rejected", "ROLLBACK;")
                results[who] = "REJECTED"
                return

        try:
            cursor.execute("COMMIT")
            timeline.add(who, "COMMIT, order confirmed", "COMMIT;")
            results[who] = "SOLD"
        except psycopg2.Error as error:
            timeline.add(who, "COMMIT failed: " + str(error).splitlines()[0])
            results[who] = "REJECTED"
    except Exception as error:
        timeline.add(who, "Error: " + str(error).splitlines()[0])
        results[who] = "ERROR"
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
    finally:
        connection.close()


def run_race(item_id, mode_label, starting_stock=1, think_time=1.0):
    mode = MODES[mode_label]
    original = database.fetch_value("SELECT stock FROM menu_item WHERE item_id = %s", (item_id,))
    database.execute("UPDATE menu_item SET stock = %s WHERE item_id = %s", (starting_stock, item_id))

    timeline = Timeline()
    results = {}
    barrier = threading.Barrier(2)
    first = threading.Thread(target=buyer, args=("Customer A", mode, item_id, timeline, results, barrier, 0.0, think_time))
    second = threading.Thread(target=buyer, args=("Customer B", mode, item_id, timeline, results, barrier, 0.15, think_time))
    first.start()
    second.start()
    first.join()
    second.join()

    final_stock = database.fetch_value("SELECT stock FROM menu_item WHERE item_id = %s", (item_id,))
    database.execute("UPDATE menu_item SET stock = %s WHERE item_id = %s", (original, item_id))

    units_sold = 0
    for who in results:
        if results[who] == "SOLD":
            units_sold += 1
    events = sorted(timeline.events, key=lambda e: e["ms"])
    return {"events": events, "results": results, "starting_stock": starting_stock, "final_stock": final_stock,
            "units_sold": units_sold, "oversold": units_sold > starting_stock or (starting_stock - units_sold) != final_stock,
            "restored_to": original}


def deadlock_worker(who, first_item, second_item, timeline, results, barrier):
    connection = database.connect(autocommit=True)
    cursor = connection.cursor()
    try:
        barrier.wait()
        cursor.execute("BEGIN")
        timeline.add(who, "BEGIN", "BEGIN;")
        cursor.execute("SELECT stock FROM menu_item WHERE item_id = %s FOR UPDATE", (first_item,))
        timeline.add(who, "Locked item " + str(first_item), "SELECT ... WHERE item_id = " + str(first_item) + " FOR UPDATE;")
        time.sleep(0.8)
        timeline.add(who, "Now wants item " + str(second_item) + " (held by the other customer)", "SELECT ... WHERE item_id = " + str(second_item) + " FOR UPDATE;")
        cursor.execute("SELECT stock FROM menu_item WHERE item_id = %s FOR UPDATE", (second_item,))
        timeline.add(who, "Got item " + str(second_item))
        cursor.execute("COMMIT")
        timeline.add(who, "COMMIT", "COMMIT;")
        results[who] = "COMMITTED"
    except psycopg2.Error as error:
        timeline.add(who, "ERROR: " + str(error).splitlines()[0])
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        timeline.add(who, "Chosen as deadlock victim, rolled back", "ROLLBACK;")
        results[who] = "ABORTED"
    finally:
        connection.close()


def run_deadlock(item_one, item_two):
    timeline = Timeline()
    results = {}
    barrier = threading.Barrier(2)
    first = threading.Thread(target=deadlock_worker, args=("Customer A", item_one, item_two, timeline, results, barrier))
    second = threading.Thread(target=deadlock_worker, args=("Customer B", item_two, item_one, timeline, results, barrier))
    first.start()
    second.start()
    first.join()
    second.join()
    events = sorted(timeline.events, key=lambda e: e["ms"])
    return {"events": events, "results": results}
