import crypt
import flask_bcrypt


def encode_password(plaintext_password: str):
    pw = flask_bcrypt.generate_password_hash(plaintext_password)
    return pw.decode('utf-8')


def check_password(password_hash, password):
    if password_hash.startswith("$2b$"):
        bs = bytes(password_hash, 'utf-8')
        return flask_bcrypt.check_password_hash(bs, password)

    if password_hash.startswith("$6$"):
        salt = password
        crypted = crypt.crypt(password, salt)
        return crypted == password_hash

    return False
