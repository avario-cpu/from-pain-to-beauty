import sqlite3

import aiosqlite
import asyncio
import constants as const

database = const.SLOTS_DB_FILE
DENIED_SLOTS_AMOUNT = 10


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
            await cur.execute('''CREATE TABLE IF NOT EXISTS denied_slots (
                                    id INTEGER PRIMARY KEY,
                                    is_open BOOLEAN NOT NULL
                               );''')
            await conn.commit()
    except aiosqlite.Error as e:
        print(e)


async def initialize_slots(conn: aiosqlite.Connection):
    try:
        async with conn.cursor() as cur:
            for i in range(0, DENIED_SLOTS_AMOUNT):
                await cur.execute(
                    '''INSERT INTO denied_slots (id, is_open) VALUES(?, ?)''',
                    (i, True))
            await conn.commit()
    except aiosqlite.Error as e:
        print(e)
        await conn.rollback()


async def delete_table(conn: aiosqlite.Connection):
    try:
        async with conn.cursor() as cursor:
            sql = "DROP TABLE IF EXISTS denied_slots"
            await cursor.execute(sql)
            await conn.commit()
            print("The table has been deleted successfully.")
    except aiosqlite.Error as e:
        print("The table has not been deleted successfully.")
        print(e)


async def occupy_first_free_slot(conn: aiosqlite.Connection) -> int | None:
    """
    Find the first free open slot in the database, populate it and return the
    slot id number as an integer. If there are no free slots, return None.
    """
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM denied_slots WHERE is_open = True LIMIT 1")
            row = await cur.fetchone()

            if row:
                slot_id = row[0]
                await cur.execute(
                    "UPDATE denied_slots SET is_open = False WHERE id = ?",
                    (slot_id,))
                await conn.commit()
                print(f"Slot {slot_id} is now populated.")
                return slot_id
            else:
                print("No free slot available.")
                await conn.commit()
                return None
    except aiosqlite.Error as e:
        print(e)
        await conn.rollback()


async def free_slot(conn: aiosqlite.Connection, slot_id: int):
    """Depopulate a slot"""
    try:
        await conn.execute("BEGIN")

        async with conn.cursor() as cur:
            await cur.execute("SELECT is_open FROM denied_slots WHERE id = ?",
                              (slot_id,))
            row = await cur.fetchone()

            if row and not row[0]:  # Ensure the slot is not already open
                await cur.execute(
                    "UPDATE denied_slots SET is_open = True WHERE id = ?",
                    (slot_id,))
                await conn.commit()
                print(f"Slot {slot_id} is now free.")
            else:
                print(f"Slot {slot_id} is already free or does not exist.")
    except aiosqlite.Error as e:
        print(e)
        await conn.rollback()


def free_slot_sync(slot_id: int):
    """Synchronous version of free_slot function"""
    conn = None
    cursor = None
    try:
        conn = sqlite3.connect(const.SLOTS_DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE denied_slots SET is_open = True WHERE id = ?", (slot_id,))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        print(e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


async def free_all_slots(conn: aiosqlite.Connection):
    """Depopulate all occupied slots"""
    try:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE denied_slots SET is_open = True")
            await conn.commit()
    except aiosqlite.Error as e:
        print(e)
        await conn.rollback()


async def main():
    conn = await create_connection(database)
    await create_table(conn)
    await initialize_slots(conn)
    slot_id = await occupy_first_free_slot(conn)
    print(f"Occupied slot: {slot_id}")
    await free_slot(conn, slot_id)
    await free_all_slots(conn)
    await delete_table(conn)
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
