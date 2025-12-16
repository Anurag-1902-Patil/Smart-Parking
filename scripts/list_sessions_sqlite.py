import sqlite3
conn = sqlite3.connect('parking.db')
cur = conn.cursor()
try:
    cur.execute('SELECT id, slot_id, is_active, start_time, end_time FROM session')
    rows = cur.fetchall()
    if not rows:
        print('NO_SESSIONS')
    for r in rows:
        print(r)
except Exception as e:
    print('ERROR', e)
finally:
    conn.close()
