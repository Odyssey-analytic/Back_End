from .QueueManager import RabbitAccountManager
from ..queue_type import queue_type
from ...models import CustomUser, Token, Queue
from ..Utilities import generate_secure_password

def GenerateToken(token_name, username, product, queues):
    token_vhost = RabbitAccountManager.create_vhost(f"{username}_{token_name}")
    token_value = generate_secure_password(64)

    token = Token.objects.create(
        name=token_name,
        value=token_value,
        Product=product
    )
    token.save()

    queue_fullnames = []
    for queue in queues:
        fullname = RabbitAccountManager.add_queue(username, token_vhost, queue["queue_name"], queue_type[queue["queue_type"]])
        q = Queue.objects.create(
            fullname=fullname,
            name=queue["queue_name"],
            type=queue["queue_type"],
            token=token
        )

        q.save()
        queue_fullnames.append(fullname)

    return token



    