import bcrypt

# Kept apart from auth.py so the seed script can hash passwords without the API's
# JWT_SECRET and API_KEY being set.


# bcrypt only uses the first 72 bytes of a password, and bcrypt 5 raises an error
# for longer ones instead of cutting them, so they are cut here.
def hash_password(password):
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def check_password(password, password_hash):
    return bcrypt.checkpw(password.encode()[:72], password_hash.encode())
