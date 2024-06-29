import sqlite3

import aiosqlite
import asyncio
import constants as const

AMOUNT_OF_SLOTS = 8
MAX_AMOUNT_OF_WINDOWS = 5  # main win counts for 1, add to that 4 secondaries
database = const.SLOTS_DB_FILE


async def create_connection(db_file: str) -> aiosqlite.Connection | None:
    db_conn = None
    try:
        db_conn = await aiosqlite.connect(db_file)
        return db_conn
    except aiosqlite.Error as e:
        print(e)
    return db_conn


async def create_table(conn: aiosqlite.Connection):
    try:
        async with conn.cursor() as cur:
            fields = ', '.join(f"name{i} TEXT, width{i} INT, height{i} INT"
                               for i in range(MAX_AMOUNT_OF_WINDOWS))

            sql = f'''CREATE TABLE IF NOT EXISTS slots (
                                id INTEGER PRIMARY KEY,
                                is_open BOOLEAN NOT NULL,
                                {fields}
                                )'''

            await cur.execute(sql)
            await conn.commit()
    except aiosqlite.Error as e:
        print(e)


async def delete_table(conn: aiosqlite.Connection):
    try:
        async with conn.cursor() as cursor:
            sql = "DROP TABLE IF EXISTS slots"
            await cursor.execute(sql)
            await conn.commit()
            print(f"The table has been deleted successfully.")
    except aiosqlite.Error as e:
        print(f"The table has not been deleted successfully.")
        print(e)
        await conn.rollback()


async def initialize_slots(conn: aiosqlite.Connection):
    """populate the table with slots id and their "is_open" bool value"""
    try:
        sql = '''INSERT INTO slots (id, is_open) 
        VALUES (?, ?)'''
        for i in range(0, AMOUNT_OF_SLOTS):
            await conn.execute(sql, (i, True))
        await conn.commit()
    except aiosqlite.Error as e:
        print(e)
        await conn.rollback()


async def occupy_slot_with_data(conn: aiosqlite.Connection, slot_id: int,
                                data: list[tuple[str, int, int]] = None):
    """Populate a target slot and insert window properties"""
    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT is_open FROM slots WHERE id = ?",
                              (slot_id,))
            row = await cur.fetchone()

            if row and row[0]:
                await cur.execute(
                    "UPDATE slots SET is_open = False WHERE id = ?",
                    (slot_id,))
                if data is not None:
                    for i in range(0, len(data)):
                        name, width, height = data[i]
                        await cur.execute(
                            f"UPDATE slots SET name{i}= ?, width{i}=?, "
                            f"height{i}=? WHERE id = ?",
                            (name, width, height, slot_id,)
                        )
                await conn.commit()
                print(f"Slot {slot_id} is now occupied.")
            else:
                print(f"Slot {slot_id} is already occupied or does not exist")
    except aiosqlite.Error as e:
        print(e)
        await conn.rollback()


async def get_first_free_slot(conn: aiosqlite.Connection) -> int | None:
    """Populate the first free open slot in the database and return it"""
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM slots WHERE is_open = True LIMIT 1")
            row = await cur.fetchone()

            if row:
                slot_id = row[0]
                await conn.commit()
                print(f"Slot {slot_id} is the first available")
                return slot_id
            else:
                print("No free slot available.")
                await conn.commit()
                return None
    except aiosqlite.Error as e:
        print(e)


async def free_slot(conn: aiosqlite.Connection, slot_id: int):
    """Depopulate a slot and removes all the data inserted into it"""
    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT is_open FROM slots WHERE id = ?",
                              (slot_id,))
            row = await cur.fetchone()

            if row and not row[0]:  # Ensure the slot is not already open
                await cur.execute(
                    "UPDATE slots SET is_open = True WHERE id = ?", (slot_id,))
                for i in range(MAX_AMOUNT_OF_WINDOWS):
                    await cur.execute(
                        f"UPDATE slots SET name{i}= ?, width{i}=?, "
                        f"height{i}=? WHERE id = ?",
                        (None, None, None, slot_id,)
                    )
                await conn.commit()
                print(f"Slot {slot_id} is now free.")
            else:
                print(f"Slot {slot_id} is already free or does not exist.")
    except aiosqlite.Error as e:
        print(e)
        await conn.rollback()


def free_slot_by_name_sync(name: str):
    """Free a slot using the main name as an identifier, rather than the
    slot_id integer. Is synchronous as to be used with atexit.register()"""
    conn = None
    cursor = None
    try:
        conn = sqlite3.connect(const.SLOTS_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT is_open, is_open FROM slots WHERE name0 = ?",
                       (name,))
        row = cursor.fetchone()
        if row:
            slot_id, is_open = row
            if not is_open:
                free_slot_sync(conn, slot_id)
                conn.commit()
            else:
                print(f"Slot {slot_id} is already free.")
        else:
            print(f"Slot named {name} does not exist.")
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        print(e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def free_slot_sync(conn: sqlite3.Connection, slot_id: int):
    """Synchronous version of free_slot function"""
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE slots SET is_open = True WHERE id = ?", (slot_id,))
        for i in range(MAX_AMOUNT_OF_WINDOWS):
            cursor.execute(
                f"UPDATE slots SET name{i}= ?, width{i}=?, "
                f"height{i}=? WHERE id = ?",
                (None, None, None, slot_id,)
            )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        print(e)
    finally:
        if cursor:
            cursor.close()


async def free_all_slots(conn: aiosqlite.Connection):
    """Free all slots and remove all their data"""
    try:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE slots SET is_open = True")

            for i in range(MAX_AMOUNT_OF_WINDOWS):
                await cur.execute(
                    f"UPDATE slots SET name{i}= ?, width{i}=?, height{i}=?",
                    (None, None, None,)
                )

            await conn.commit()

    except aiosqlite.Error as e:
        print(e)
        await conn.rollback()


async def get_full_data(conn: aiosqlite.Connection, slot_id) \
        -> list[tuple[str, int, int]] | None:
    """Get all the data from a row (window name and size), excludes is_open.
    Ingres null data."""
    try:
        async with conn.cursor() as cur:
            fields = ', '.join([f"name{i}, width{i}, height{i}"
                                for i in range(MAX_AMOUNT_OF_WINDOWS)])
            sql = f"SELECT {fields} FROM slots WHERE id = ?"
            await cur.execute(sql, (slot_id,))
            row = await cur.fetchone()

            if row:
                data = []
                for i in range(0, len(row), 3):
                    data_tuple = (row[i], row[i + 1], row[i + 2])
                    if not all(element is None for element in data_tuple):
                        data.append(data_tuple)
                return data
            else:
                return None

    except aiosqlite.Error as e:
        print(e)
        return None


async def get_slot_by_main_name(conn: aiosqlite.Connection,
                                name: str) -> int | None:
    """Get the slot id by the main name"""
    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM slots WHERE name0 = ?", (name,))
            row = await cur.fetchone()
            if row:
                return row[0]
            else:
                print(f"No slot found with the main name: {name}")
                return None
    except aiosqlite.Error as e:
        print(e)
        return None


async def get_all_names(conn: aiosqlite.Connection) -> list[str]:
    """Get a list of all the names, main and secondary,
     in the entire database"""
    try:
        async with conn.cursor() as cur:
            names = []
            for i in range(MAX_AMOUNT_OF_WINDOWS):
                await cur.execute(f"SELECT name{i} FROM slots")
                rows = await cur.fetchall()

                for row in rows:
                    name = row[0]
                    if name is not None:
                        names.append(name)
            return names

    except aiosqlite.Error as e:
        print(e)
        return []


async def get_all_occupied_slots(conn: aiosqlite.Connection) -> list[int]:
    """Get a list of all the occupied slots ids"""
    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM slots WHERE is_open = False")
            rows = await cur.fetchall()
            slot_ids = []
            if rows is not None:
                for row in rows:
                    slot_ids.append(row[0])
                return slot_ids
            else:
                print('No occupied slots found')
            pass
    except aiosqlite.Error as e:
        print(e)
        return []


async def get_all_free_slots(conn: aiosqlite.Connection) -> list[int]:
    """Get a list of all the free slots ids"""
    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM slots WHERE is_open = True")
            rows = await cur.fetchall()
            slot_ids = []
            if rows is not None:
                for row in rows:
                    slot_ids.append(row[0])
                return slot_ids
            else:
                print('No free slots found')
    except aiosqlite.Error as e:
        print(e)
        return []


async def main():
    conn = await create_connection(database)
    await delete_table(conn)
    await create_table(conn)
    await initialize_slots(conn)
    await occupy_slot_with_data(conn, 1,
                                [("main", 800, 600), ("secondary1", 400, 300)])
    await free_slot(conn, 1)
    all_names = await get_all_names(conn)
    all_occupied = await get_all_occupied_slots(conn)
    all_free = await get_all_free_slots(conn)
    print(all_names)
    print(all_occupied)
    print(all_free)

    await conn.close()  # Ensure to close the connection when done


if __name__ == "__main__":
    asyncio.run(main())
