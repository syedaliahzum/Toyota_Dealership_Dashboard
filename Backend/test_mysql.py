import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",        # or your MySQL user
    password="11223344",
    database="toyota"
)

print("Connected:", conn.is_connected())
conn.close()
