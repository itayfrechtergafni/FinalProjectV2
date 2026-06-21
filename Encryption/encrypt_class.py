import os
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

iv_size = 12          # AES-GCM standard init-vector length
rsa_key_size = 2048   # RSA key size in bits

# --- handshake markers sent in PLAINTEXT ---

HELLO_FLAG = b"__HELLO__"     # client -> server: "give me your public key"
PUBKEY_FLAG = b"__GET_PUBLIC_KEY__"   # server -> client: PUBKEY_FLAG + <rsa public key (PEM)>
AESKEY_FLAG = b"__GET_MY_AES_KEY__"   # client -> server: AESKEY_FLAG + <aes key, RSA-encrypted>
_ACK = b"OK"                # server -> client: AES-encrypted, confirms handshake


#  RSA helpers

def create_rsa_keys():
    private_key = RSA.generate(rsa_key_size)
    return private_key, private_key.publickey()


def rsa_encrypt(data: bytes, public_key) -> bytes:
    return PKCS1_OAEP.new(public_key).encrypt(data)


def rsa_decrypt(blob: bytes, private_key) -> bytes:
    return PKCS1_OAEP.new(private_key).decrypt(blob)


def export_public_key(public_key) -> bytes:
    return public_key.export_key()          # PEM bytes


def import_public_key(blob: bytes):
    return RSA.import_key(blob)


#  AES helpers

def new_aes_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def _gcm(aes_key):
    # if key isn't type AESGCM turn it into an AESGCM object
    return aes_key if isinstance(aes_key, AESGCM) else AESGCM(aes_key)


def aes_encrypt_bytes(data: bytes, aes_key) -> bytes:
    iv = os.urandom(iv_size)
    return iv + _gcm(aes_key).encrypt(iv, data, None)


def aes_decrypt_bytes(blob: bytes, aes_key) -> bytes:
    iv, ciphertext = blob[:iv_size], blob[iv_size:]
    return _gcm(aes_key).decrypt(iv, ciphertext, None)


def aes_encrypt(message: str, aes_key) -> str:
    return base64.b64encode(aes_encrypt_bytes(message.encode("utf-8"), aes_key)).decode("ascii")


def aes_decrypt(token: str, aes_key) -> str:
    return aes_decrypt_bytes(base64.b64decode(token), aes_key).decode("utf-8")


#  Transport wrappers  (explicit key -- used by the SERVER, which holds a different key per client address)

def secure_sendto(sock, data: bytes, addr, aes_key):
    return sock.sendto(aes_encrypt_bytes(data, aes_key), addr)


def secure_recvfrom(sock, bufsize, aes_key):
    blob, addr = sock.recvfrom(bufsize)
    return aes_decrypt_bytes(blob, aes_key), addr


#  SERVER side handshake

def server_handle_handshake(sock, raw, addr, private_key, public_key, keys):
    """Process a possibly-handshake datagram.

    Returns True if `raw` was a handshake packet (and was handled here), or
    False if it is ordinary (encrypted) application data the caller must
    decrypt with keys[addr].
    """

    if raw == HELLO_FLAG:
        sock.sendto(PUBKEY_FLAG + export_public_key(public_key), addr)
        return True
    if raw.startswith(AESKEY_FLAG):
        try:
            aes_key = rsa_decrypt(raw[len(AESKEY_FLAG):], private_key)
            keys[addr] = aes_key
            # Confirm with an AES-encrypted ack so the client knows we're set.
            sock.sendto(aes_encrypt_bytes(_ACK, aes_key), addr)
        except Exception as e:
            print("handshake error:", e)
        return True
    return False


#  CLIENT side handshake + per-socket key registry


# Each client socket talks to exactly one server, so it has exactly one AES key.
# We stash it here keyed by the socket object so the rest of the client code can stay simple.
_client_keys = {}   # id(sock) -> raw aes key


def client_handshake(sock):
    """get the rsa public key and send our aes key encrypted"""
    aes_key = new_aes_key()
    sock.send(HELLO_FLAG)
    reply = sock.recv(65535)
    public_key = import_public_key(reply[len(PUBKEY_FLAG):])
    sock.send(AESKEY_FLAG + rsa_encrypt(aes_key, public_key))
    sock.recv(65535)  # wait for the server's ack so we know it stored our key
    _client_keys[id(sock)] = aes_key
    return aes_key


def get_key(sock):
    return _client_keys.get(id(sock))


def client_send(sock, data: bytes, addr):
    """Client-side secure send: encrypts with this socket's own key."""
    return secure_sendto(sock, data, addr, _client_keys[id(sock)])


def client_recv(sock, bufsize):
    """Client-side secure recv: decrypts with this socket's own key."""
    return secure_recvfrom(sock, bufsize, _client_keys[id(sock)])
