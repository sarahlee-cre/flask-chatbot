import secrets

secret_key = secrets.token_hex(16)
print("FLASK_SECRET_KEY =", secret_key)
