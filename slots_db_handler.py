import sqlite3


def create_connection(db_file):
    db_conn = None
    try:
        db_conn = sqlite3.connect(db_file)
        return db_conn
    except sqlite3.Error as e:
        print(e)
    return db_conn


def create_tables():
    try:
        sql = '''CREATE TABLE IF NOT EXISTS slots (
                    id integer PRIMARY KEY,
                    is_open boolean NOT NULL,
                    name TEXT,
                    has_secondary_windows boolean NOT NULL
                );

                    CREATE TABLE IF NOT EXISTS secondary_names (
                    id INTEGER PRIMARY KEY,
                    slot_id INTEGER,
                    name1 TEXT,
                    name2 TEXT,
                    name3 TEXT,
                    name4 TEXT,
                    FOREIGN KEY (slot_id) REFERENCES slots (id)
                );'''

        cur = conn.cursor()
        cur.execute(sql)

    except sqlite3.Error as e:
        print(e)


def delete_table():
    try:
        cursor = conn.cursor()
        sql = f"DROP TABLE IF EXISTS slots"
        cursor.execute(sql)
        conn.commit()
        print(f"The table has been deleted successfully.")
    except sqlite3.Error as e:
        print(f"The table has not been deleted successfully.")
        print(e)
        conn.rollback()


def initialize_slots():
    try:
        sql = '''INSERT INTO slots (id, is_open) VALUES (?, ?)'''
        for i in range(0, 8):
            conn.execute(sql, (i, True))  # Initially all slots are open
        conn.commit()
    except sqlite3.Error as e:
        print(e)


def check_slots():
    """ Check which slots are open and which are not """
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, is_open FROM slots")
        rows = cur.fetchall()
        for row in rows:
            print(f"Slot {row[0]} is {'open' if row[1] else 'not open'}")
        conn.commit()
    except sqlite3.Error as e:
        print(e)


def free_all_occupied_slots():
    try:
        conn.execute("BEGIN")

        # Fetch all occupied slots
        cur = conn.cursor()
        cur.execute("SELECT id FROM slots WHERE is_open = False")
        rows = cur.fetchall()

        if rows:
            for row in rows:
                slot_id = row[0]
                # Update the status of the identified slot to 'open'
                cur.execute("UPDATE slots SET is_open = True WHERE id = ?",
                            (slot_id,))
                # Set the name of the slot back to null
                cur.execute("UPDATE slots SET name = null WHERE id = ?",
                            (slot_id,))
                conn.commit()
                print(f"Slot {slot_id} is now free.")
    except sqlite3.Error as e:
        print(e)
        conn.rollback()


def occupy_all_free_slots():
    """Used only for debugging"""
    try:
        conn.execute("BEGIN")

        # Fetch all free slots
        cur = conn.cursor()
        cur.execute("SELECT id FROM slots WHERE is_open = True")
        rows = cur.fetchall()

        if rows:
            for row in rows:
                slot_id = row[0]
                # Update the status of the identified slot to 'closed'
                cur.execute("UPDATE slots SET is_open = False WHERE id = ?",
                            (slot_id,))
                print(f"Slot {slot_id} is now occupied.")
            conn.commit()
        else:
            print("No free slots found.")
    except sqlite3.Error as e:
        print(e)
        conn.rollback()


def populate_first_free_slot() -> int | None:
    """Find the first free open slot in the database and return the slot id
    number as an integer. If there are no free slots, return None"""
    try:
        conn.execute("BEGIN")
        cur = conn.cursor()
        cur.execute("SELECT id FROM slots WHERE is_open = True LIMIT 1")
        row = cur.fetchone()

        if row:
            slot_id = row[0]
            cur.execute("UPDATE slots SET is_open = False WHERE id = ?",
                        (slot_id,))
            conn.commit()
            print(f"Slot {slot_id} is now populated.")
            return slot_id
        else:
            print("No free slots available.")
            conn.commit()
            return None
    except sqlite3.Error as e:
        print(e)
        conn.rollback()


def name_slot(slot_id: int, name: str):
    try:
        conn.execute("BEGIN")

        cur = conn.cursor()
        cur.execute("SELECT name FROM slots WHERE id = ?", (slot_id,))
        row = cur.fetchone()

        if row:
            cur.execute("UPDATE slots SET name = ? WHERE id = ?",
                        (name, slot_id))
            conn.commit()
            print(f"Slot {slot_id} named {name}.")
    except sqlite3.Error as e:
        print(e)
        conn.rollback()


def get_all_names():
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM slots")
        rows = cur.fetchall()

        # Extracting the names from each row
        names = [row[0] for row in rows if row[0] is not None]

        return names
    except sqlite3.Error as e:
        print(e)
        return []


def free_slot(slot_id: int):
    try:
        conn.execute("BEGIN")

        # Check if the slot is currently occupied
        cur = conn.cursor()
        cur.execute("SELECT is_open FROM slots WHERE id = ?", (slot_id,))
        row = cur.fetchone()

        if row and not row[0]:  # Ensure the slot is not already open
            # Update the status of the identified slot to 'open'
            cur.execute("UPDATE slots SET is_open = True WHERE id = ?",
                        (slot_id,))
            # Set the name of the slot back to null
            cur.execute("UPDATE slots SET name = null WHERE id = ?",
                        (slot_id,))
            conn.commit()
            print(f"Slot {slot_id} is now free.")
        else:
            print(f"Slot {slot_id} is already free or does not exist.")
    except sqlite3.Error as e:
        print(e)
        conn.rollback()


database = "slots.db"
conn = create_connection(database)


def recreate_table():
    if conn is not None:
        delete_table()
        create_tables()
        initialize_slots()
        check_slots()
    else:
        print("Error! Cannot create the database connection.")
    if conn:
        conn.close()

# delete_table()
create_tables()
# recreate_table()
# populate_first_free_slot()
# occupy_all_free_slots()
# free_slot(2)
# initialize_slots()
# name_slot(2, "lol")
