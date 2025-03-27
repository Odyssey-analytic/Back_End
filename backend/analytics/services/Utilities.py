import secrets
import string
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

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