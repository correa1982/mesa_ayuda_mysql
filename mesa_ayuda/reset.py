# create_admin.py  (temporal)
from flask import Flask
from werkzeug.security import generate_password_hash
from mesa.db import get_db, close_db

USERNAME = "admin"
DISPLAY_NAME = "Administrador"
PASSWORD = "1234"  # cámbiala si quieres
ROLE = "admin"

app = Flask(__name__)
with app.app_context():
    db = get_db()
    # INSERT si no existe; si existe, actualiza contraseña y activa rol admin
    db.execute(
        """
        INSERT INTO users (username, display_name, password_hash, role, created_at)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            display_name=VALUES(display_name),
            password_hash=VALUES(password_hash),
            role=VALUES(role)
        """,
        (USERNAME, DISPLAY_NAME, generate_password_hash(PASSWORD), ROLE, __import__("datetime").datetime.utcnow().isoformat())
    )
    db.commit()
    close_db()
print("✅ Usuario admin creado/actualizado.")