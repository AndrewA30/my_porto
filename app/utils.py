from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

def hash_password(password: str):
    return password_hash.hash(password)

def verify_password(input_password: str, hased_password:str):
    return password_hash.verify(input_password, hased_password)
