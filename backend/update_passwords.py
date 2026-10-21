import pymysql
from app.infrastructure.security.password_hasher import PasswordHasher

password = "KddlDemo!2026"
hasher = PasswordHasher()
hashed = hasher.hash(password)
print(f"Generated hash: {hashed}")

conn = pymysql.connect(
    host="localhost",
    user="root",
    password="Sahil@123",
    database="kddl_neww",
    port=3306,
    autocommit=True
)

with conn.cursor() as cursor:
    sql = "UPDATE users SET password_hash = %s"
    affected = cursor.execute(sql, (hashed,))
    print(f"Successfully updated {affected} users with password: {password}")

conn.close()
