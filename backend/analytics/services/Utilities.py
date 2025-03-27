import secrets
import string
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import hashlib
import base64

def generate_secure_password(length=12):
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def send_update_to_group(message, group):
    channel_layer = get_channel_layer()
    print(channel_layer)
    async_to_sync(channel_layer.group_send)(
    group,
    {
        "type": "send.sse.message",
        "text": message,
    }
)

def secure_hash_base64(input_string):
    sha256_hash = hashlib.sha256()
    sha256_hash.update(input_string.encode('utf-8'))    
    hashed_bytes = sha256_hash.digest()
    
    base64_encoded_hash = base64.b64encode(hashed_bytes).decode('utf-8')
    filtered_hash = ''.join([char for char in base64_encoded_hash if char.isalpha()])
    
    return filtered_hash