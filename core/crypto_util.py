import os
import json
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes

# WARNING: Key management is insecure. This is for demonstration.
SECRET_KEY = b'super-secret-key-that-should-be-stored-securely' 
SALT = b'fixed-salt-for-demo'

def encrypt(data):
    key = PBKDF2(SECRET_KEY, SALT, dkLen=32)
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(data.encode('utf-8'))
    return cipher.nonce.hex() + ciphertext.hex() + tag.hex()

def decrypt(encrypted_data):
    key = PBKDF2(SECRET_KEY, SALT, dkLen=32)
    raw = bytes.fromhex(encrypted_data)
    nonce = raw[:16]
    ciphertext = raw[16:-16]
    tag = raw[-16:]
    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')
