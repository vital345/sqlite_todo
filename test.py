import sqlite3

conn = sqlite3.connect('tododatabase.sqlite', check_same_thread=False)
cur = conn.cursor()


cur.execute('''
INSERT INTO status (user_id ,task_id, remainders)

VALUES ( ? , ? , ? )''', (28793, 5, 'Remainder for me'))
conn.commit()

cur.execute(
'''
SELECT * FROM status WHERE user_id = ?
''', (28793, ))
user_task = cur.fetchone()

print(user_task)