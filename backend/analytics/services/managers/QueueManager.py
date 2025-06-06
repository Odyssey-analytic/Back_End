from ..queue_type import queue_type
import requests
from requests.auth import HTTPBasicAuth
from ..Utilities import generate_secure_password, secure_hash_base64
from backend.celery import add_queue, delete_queue
from django.conf import settings 

class RabbitAccountManager:
    def __init__(self, client):
        self.client_name = client
        self.passowrdlength = 64 

    @staticmethod
    def account_exist(username):
        check_response = requests.get(
            f"{settings.RABBITMQ_API_URL}/users/{username}",
            auth=HTTPBasicAuth(settings.ADMIN_USER, settings.ADMIN_PASS),
            timeout=10
        )
        if check_response.status_code == 200:
            return True
        if check_response.status_code == 404:
            return False
    
    @staticmethod
    def create_vhost(username):
        vhost_name = f"{username}_vhost"

        create_vhost_response = requests.put(
            f"{settings.RABBITMQ_API_URL}/vhosts/{vhost_name}",
            auth=HTTPBasicAuth(settings.ADMIN_USER, settings.ADMIN_PASS),
            timeout=10
        )

        if create_vhost_response.status_code in [201, 204]:
            print(f"Vhost '{vhost_name}' created successfully.")
        elif create_vhost_response.status_code == 400:
            print(f"Bad request while creating vhost: {create_vhost_response.text}")
            raise ValueError("Bad request during vhost creation")
        else:
            print(f"Unexpected response while creating vhost: {create_vhost_response.status_code} - {create_vhost_response.text}")
            raise ValueError("Unexpected response during vhost creation")
        
        permissions_response = requests.put(
                f"{settings.RABBITMQ_API_URL}/permissions/{vhost_name}/{username}",
                auth=HTTPBasicAuth(settings.ADMIN_USER, settings.ADMIN_PASS),
                json={
                    "configure": "",  
                    "write": ".*",    
                    "read": ""        
                },
                timeout=10
            )
        return vhost_name

    def delete_vhost(self, vhost_name):
        delete_response = requests.delete(
            f"{settings.RABBITMQ_API_URL}/vhosts/{vhost_name}",
            auth=HTTPBasicAuth(settings.ADMIN_USER, settings.ADMIN_PASS),
            timeout=10
        )

        if delete_response.status_code == 204:
            print(f"Vhost '{vhost_name}' deleted successfully.")
        elif delete_response.status_code == 404:
            print(f"Vhost '{vhost_name}' not found.")
            raise KeyError(f"Vhost '{vhost_name}' does not exist.")
        else:
            print(f"Unexpected response while deleting vhost: {delete_response.status_code} - {delete_response.text}")
            raise ValueError("Failed to delete vhost")

    def create_account(self):
        username = self.client_name
        password = generate_secure_password(self.passowrdlength)

        if self.account_exist(username):
            print(f"User '{username}' already exists. No action performed.")
            raise KeyError("account with this username already exists")
        else:
            create_response = requests.put(
                f"{settings.RABBITMQ_API_URL}/users/{username}",
                auth=HTTPBasicAuth(settings.ADMIN_USER, settings.ADMIN_PASS),
                json={
                    "password": password,
                    "tags": ["management"]
                },
                timeout=10
            )
            print(repr(create_response._content))
            if create_response.status_code == 201:
                print(f"User '{username}' created successfully.")
            elif create_response.status_code == 400:
                print(f"Bad Request in the way to rabbitMQ: {create_response.text}")
                raise ValueError("Bad request")
            else:
                print(f"Unexpected response: {create_response.status_code} - {create_response.text}")
                raise ValueError("Unexpected response")

            set_permissions = requests.put(
                f"{settings.RABBITMQ_API_URL}/permissions/{settings.RABBITMQ_VHOST}/{username}",
                auth=HTTPBasicAuth(settings.ADMIN_USER, settings.ADMIN_PASS),
                json={
                    "configure": "",
                    "write": ".*",
                    "read": ""
                },
                timeout=10
            )



            return (username, password)
            
    def remove_account(self):
        username = self.client_name
        delete_response = requests.delete(
            f"{settings.RABBITMQ_API_URL}/users/{username}",
            auth=HTTPBasicAuth(settings.ADMIN_USER, settings.ADMIN_PASS),
            timeout=10
        )

        if delete_response.status_code == 204:
            print(f"User '{username}' deleted successfully.")
        elif delete_response.status_code == 404:
            print(f"User '{username}' not found in RabbitMQ.")
            raise KeyError("User not found in RabbitMQ")
        else:
            print(f"Unexpected response: {delete_response.status_code} - {delete_response.text}")
            raise ValueError("Unexpected response")

    @staticmethod
    def add_queue(username, VHOST, queue_name: str, queue_type: queue_type):
        queue_name = f"{username}.{VHOST}.{queue_name}.{queue_type.name}"  
        #queue_name = secure_hash_base64(queue_name)
        print(f"{settings.RABBITMQ_API_URL}/queues/{settings.RABBITMQ_VHOST}/{queue_name}")
        print(settings.ADMIN_USER, settings.ADMIN_PASS)
        create_queue_response = requests.put(
            f"{settings.RABBITMQ_API_URL}/queues/{settings.RABBITMQ_VHOST}/{queue_name}",
            auth=HTTPBasicAuth(settings.ADMIN_USER, settings.ADMIN_PASS),
            json={
                "durable": True
            },
            timeout=10
        )

        if create_queue_response.status_code == 201 or create_queue_response.status_code == 204:
            print(f"Queue '{queue_name}' created successfully.")
            print("firing add queue task")
            add_queue.delay(queue_name)
            return queue_name
        elif create_queue_response.status_code == 400:
            print(f"Bad request while creating queue: {create_queue_response.text}")
            raise ValueError("Bad request during queue creation")
        else:
            print(f"Unexpected response while creating queue: {create_queue_response.status_code} - {create_queue_response.text}")
            raise ValueError("Unexpected response during queue creation")
            
    def remove_queue(self, VHOST, queue_name):
        full_queue_name = f"{queue_name}"

        delete_response = requests.delete(
            f"{settings.RABBITMQ_API_URL}/queues/{VHOST}/{full_queue_name}",
            auth=HTTPBasicAuth(settings.ADMIN_USER, settings.ADMIN_PASS),
            timeout=10
        )

        if delete_response.status_code in [204, 200]:
            print(f"Queue '{full_queue_name}' deleted successfully from vhost '{VHOST}'.")
            print("firing delete queue task")
            delete_queue.delay(queue_name)
        elif delete_response.status_code == 404:
            print(f"Queue '{full_queue_name}' not found in vhost '{VHOST}'. Nothing to delete.")
            raise KeyError(f"Queue '{full_queue_name}' does not exist.")
        else:
            print(f"Unexpected response while deleting queue: {delete_response.status_code} - {delete_response.text}")
            raise ValueError("Failed to delete queue")
