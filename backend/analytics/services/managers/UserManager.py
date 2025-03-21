from ..queue_manager import RabbitAccountManager
from ..queue_type import queue_type
from ...models import User, Token, Queue
from ..Utilities import generate_secure_password
class UserManager:
    
    def __init__(self):
        pass

    def __init__(self, name):
        self.load_user(name)

    def create_user(self, name):
            self.account_manager = RabbitAccountManager(name)
            username, password = self.account_manager.create_account()
            
            user = User.objects.create(
                name=name,
                rb_username=username,
                rb_password=password
            )
            user.save()
            
            self.user = user
            return user
    
    def load_user(self, name):
        self.user = User.objects.get(id=name)
        self.account_manager = RabbitAccountManager(name)

    def add_token(self, token_name: str, queues: list[dict[str:str]]):
        token_vhost = self.account_manager.create_vhost(self.user.name)
        token_value = generate_secure_password(64)

        token = Token.objects.create(
            name=token_name,
            value=token_value,
            VHOST_name=token_vhost,
            user=self.user
        )
        
        queue_fullnames = []
        for queue in queues:
            fullname = self.account_manager.add_queue(token_vhost, queue["queue_name"], queue_type[queue["queue_type"]])
            Queue.objects.create(
                fullname=fullname,
                name=queue["queue_name"],
                type=queue["queue_type"],
                token=token
            )
            queue_fullnames.append(fullname)


    