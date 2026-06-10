import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


_KEY = b"talkhobi_secret_aes_key_32bytes!"
iv_size = 12  # GCM standard init vector length

_aesgcm = AESGCM(_KEY)


def encrypt_bytes(data: bytes):
    iv = os.urandom(iv_size)
    return iv + _aesgcm.encrypt(iv, data, None)


def decrypt_bytes(blob: bytes):
    iv, ciphertext = blob[:iv_size], blob[iv_size:]
    return _aesgcm.decrypt(iv, ciphertext, None)


def encrypt(message: str):
    return base64.b64encode(encrypt_bytes(message.encode("utf-8"))).decode("ascii")


def decrypt(token: str) -> str:
    return decrypt_bytes(base64.b64decode(token)).decode("utf-8")


# --- socket transport wrappers: encrypt on send, decrypt on recv ---
# Drop-in replacements for sock.sendto / sock.recvfrom so EVERY datagram on the
# wire is ciphertext. The whole packet is encrypted, so SEP / flags / user ids
# are all hidden; the existing parsing runs on the decrypted plaintext exactly
# as before. Raw bytes (no base64) here to keep audio/video packets small.
def secure_sendto(sock, data: bytes, addr):
    return sock.sendto(encrypt_bytes(data), addr)


def secure_recvfrom(sock, bufsize):
    blob, addr = sock.recvfrom(bufsize)
    return decrypt_bytes(blob), addr
