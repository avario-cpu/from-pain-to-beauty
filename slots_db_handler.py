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
AMOUNT_OF_SLOTS = 8
AMOUNT_OF_WINDOWS = 5  # main counts for 1, then secondaries


def create_table():
    try:
        cur = conn.cursor()
        fields = ', '.join(f"name{i} TEXT, width{i} INT, height{i} INT"
                           for i in range(AMOUNT_OF_WINDOWS))

        sql = f'''CREATE TABLE IF NOT EXISTS slots (
                            id INTEGER PRIMARY KEY,
                            is_open BOOLEAN NOT NULL,
                            {fields}
                            )'''

        cur.execute(sql)
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")


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
    """populate the table with slots id and their "is_open" bool value"""
    try:
        sql = '''INSERT INTO slots (id, is_open) 
        VALUES (?, ?)'''
        for i in range(0, AMOUNT_OF_SLOTS):
            conn.execute(sql, (i, True))
        conn.commit()
    except sqlite3.Error as e:
        print(e)


def occupy_slot_with_data(slot_id: int, data: list[tuple] = None):
    """Populate a target slot and insert window properties"""
    try:

        cur = conn.cursor()
        cur.execute("SELECT is_open FROM slots WHERE id = ?", (slot_id,))
        row = cur.fetchone()

        if row and row[0]:
            cur.execute("UPDATE slots SET is_open = False WHERE id = ?",
                        (slot_id,))
            if data is not None:
                for i in range(0, len(data)):
                    name, width, height = data[i]
                    cur.execute(
                        f"UPDATE slots SET name{i}= ?, width{i}=?, "
                        f"height{i}=? WHERE id = ?",
                        (name, width, height, slot_id,))
            conn.commit()
            print(f"Slot {slot_id} is now occupied.")
        else:
            print(f"Slot {slot_id} is already occupied or does not exist")
    except sqlite3.Error as e:
        print(e)
        conn.rollback()


def get_first_free_slot() -> int | None:
    """Populate the first free open slot in the database and return it"""
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM slots WHERE is_open = True LIMIT 1")
        row = cur.fetchone()

        if row:
            slot_id = row[0]
            conn.commit()
            print(f"Slot {slot_id} is the first available")
            return slot_id
        else:
            print("No free slot available.")
            conn.commit()
            return None
    except sqlite3.Error as e:
        print(e)
        conn.rollback()


def set_slot_main_name(slot_id: int, name: str):
    """Set the main name of a slot"""
    try:
        cur = conn.cursor()
        cur.execute("SELECT name0 FROM slots WHERE id = ?", (slot_id,))
        row = cur.fetchone()

        if row:
            cur.execute("UPDATE slots SET name0 = ? WHERE id = ?",
                        (name, slot_id))
            conn.commit()
            print(f"Slot {slot_id} named {name}.")
    except sqlite3.Error as e:
        print(e)
        conn.rollback()


def free_slot(slot_id: int):
    """Depopulate a slot and removes all the data inserted into it"""
    try:

        cur = conn.cursor()
        cur.execute("SELECT is_open FROM slots WHERE id = ?", (slot_id,))
        row = cur.fetchone()

        if row and not row[0]:  # Ensure the slot is not already open
            cur.execute("UPDATE slots SET is_open = True WHERE id = ?",
                        (slot_id,))
            # Set the names of the slot back to null
            for i in range(AMOUNT_OF_WINDOWS):
                cur.execute(
                    f"UPDATE slots SET name{i}= ?, width{i}=?, height{i}=?"
                    f"WHERE id =? ",
                    (None, None, None, slot_id,))
            conn.commit()
            print(f"Slot {slot_id} is now free.")
        else:
            print(f"Slot {slot_id} is already free or does not exist.")
    except sqlite3.Error as e:
        print(e)
        conn.rollback()


def free_slot_named(name):
    """Free a slot using the main name as an identifier rather than the slot id
    integer"""
    cur = conn.cursor()
    cur.execute("SELECT id FROM slots WHERE name0 = ?", (name,))
    row = cur.fetchone()
    if row:
        free_slot(row[0])


def free_all_slots():
    """Free all slots and remove all their data"""
    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE slots SET is_open = True")

        for i in range(AMOUNT_OF_WINDOWS):
            cur.execute(
                f"UPDATE slots SET name{i}= ?, width{i}=?, height{i}=?",
                (None, None, None,))

        conn.commit()

    except sqlite3.Error as e:
        print(e)
        conn.rollback()


def get_full_data(slot_id) -> list[str]:
    """Get all the data from a row (window name and size, excludes is_open)"""
    try:
        cur = conn.cursor()

        fields = ', '.join([f"name{i}, width{i}, height{i}"
                            for i in range(AMOUNT_OF_WINDOWS)])

        sql = f"SELECT {fields} FROM slots WHERE id = ?"

        cur.execute(sql, (slot_id,))
        row = cur.fetchone()
        print(row)
        return row

    except sqlite3.Error as e:
        print(e)


def get_slot_by_main_name(name: str) -> int | None:
    """Get the slot id by the main name"""
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM slots WHERE name0 = ?", (name,))
        row = cur.fetchone()
        if row:
            return row[0]
        else:
            print(f"No slot found with the main name: {name}")
            return None
    except sqlite3.Error as e:
        print(e)
        return None


def get_all_names() -> list[str]:
    """Get a list of all the names, main and secondary, in the entire
    database"""
    try:
        cur = conn.cursor()
        names = []
        for i in range(AMOUNT_OF_WINDOWS):
            cur.execute(f"SELECT name{i} FROM slots")
            rows = cur.fetchall()

            for row in rows:
                name = row[0]
                if name is not None:
                    names.append(name)
        return names

    except sqlite3.Error as e:
        print(e)
        return []


def get_all_occupied_slots() -> list[int]:
    """Get a list of all the occupied slots ids"""
    cur = conn.cursor()
    cur.execute("SELECT id FROM slots WHERE is_open = False")
    rows = cur.fetchall()
    slot_ids = []
    if rows is not None:
        for row in rows:
            slot_ids.append(row[0])
        return slot_ids
    else:
        print('No occupied slots found')
    pass


def get_all_free_slots() -> list[int]:
    """Get a list of all the free slots ids"""
    cur = conn.cursor()
    cur.execute("SELECT id FROM slots WHERE is_open = True")
    rows = cur.fetchall()
    slot_ids = []
    if rows is not None:
        for row in rows:
            slot_ids.append(row[0])
        return slot_ids
    else:
        print('No free slots found')
