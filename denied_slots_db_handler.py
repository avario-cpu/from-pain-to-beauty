import sqlite3


def create_connection(db_file):
    db_conn = None
    try:
        db_conn = sqlite3.connect(db_file)
        return db_conn
    except sqlite3.Error as e:
        print(e)
    return db_conn


database = "slots.db"
conn = create_connection(database)
amount_of_slots = 10


def create_table():
    try:
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS denied_slots (
                            id INTEGER PRIMARY KEY,
                            is_open BOOLEAN NOT NULL
                       );''')
    except sqlite3.Error as e:
        print(e)


def initialize_slots():
    try:
        cur = conn.cursor()
        for i in range(0, amount_of_slots):
            cur.execute('''INSERT INTO denied_slots (id, is_open) VALUES(?, 
            ?)''', (i, True))
        conn.commit()
    except sqlite3.Error as e:
        print(e)
        conn.rollback()


def check_slots():
    """ Check which slots are open and which are not """
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, is_open FROM denied_slots")
        rows = cur.fetchall()
        for row in rows:
            print(f"Slot {row[0]} is {'open' if row[1] else 'not open'}")
        conn.commit()
    except sqlite3.Error as e:
        print(e)


def delete_table():
    try:
        cursor = conn.cursor()
        sql = f"DROP TABLE IF EXISTS denied_slots"
        cursor.execute(sql)
        conn.commit()
        print(f"The table has been deleted successfully.")
    except sqlite3.Error as e:
        print(f"The table has not been deleted successfully.")
        print(e)
        conn.rollback()


def occupy_first_free_slot() -> int | None:
    """
    Find the first free open slot in the database, populate it and return the
    slot id number as an integer. If there are no free slots, return None.
    """
    try:
        conn.execute("BEGIN")
        cur = conn.cursor()
        cur.execute("SELECT id FROM denied_slots WHERE is_open = True LIMIT 1")
        row = cur.fetchone()

        if row:
            slot_id = row[0]
            cur.execute("UPDATE denied_slots SET is_open = False WHERE id = ?",
                        (slot_id,))
            conn.commit()
            print(f"Slot {slot_id} is now populated.")
            return slot_id
        else:
            print("No free slot available.")
            conn.commit()
            return None
    except sqlite3.Error as e:
        print(e)
        conn.rollback()


def free_slot(slot_id: int):
    """Depopulate a slot"""
    try:
        conn.execute("BEGIN")

        cur = conn.cursor()
        cur.execute("SELECT is_open FROM denied_slots WHERE id = ?",
                    (slot_id,))
        row = cur.fetchone()

        if row and not row[0]:  # Ensure the slot is not already open
            cur.execute("UPDATE denied_slots SET is_open = True WHERE id = ?",
                        (slot_id,))
            conn.commit()
            print(f"Slot {slot_id} is now free.")
        else:
            print(f"Slot {slot_id} is already free or does not exist.")
    except sqlite3.Error as e:
        print(e)
        conn.rollback()


def free_all_occupied_slots():
    """Depopulate all occupied slots"""
    try:
        conn.execute("BEGIN")

        # Fetch all occupied slots
        cur = conn.cursor()
        cur.execute("SELECT id FROM denied_slots WHERE is_open = False")
        rows = cur.fetchall()

        if rows:
            for row in rows:
                slot_id = row[0]
                cur.execute(
                    "UPDATE denied_slots SET is_open = True WHERE id = ?",
                    (slot_id,))
                conn.commit()
                print(f"Slot {slot_id} is now free.")
    except sqlite3.Error as e:
        print(e)
        conn.rollback()

