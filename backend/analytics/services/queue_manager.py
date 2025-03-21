from .queue_type import queue_type
import requests
from requests.auth import HTTPBasicAuth
from .Utilities import generate_secure_password

class RabbitAccountManager:
    def __init__(self, client):
        self.client = client
        self.RABBITMQ_API_URL = "http://localhost:15672/api"
        self.ADMIN_USER = "guest"
        self.ADMIN_PASS = "guest"
        self.tags = "management"
        self.passowrdlength = 64 

    def account_exist(self, username):
        check_response = requests.get(
            f"{self.RABBITMQ_API_URL}/users/{username}",
            auth=HTTPBasicAuth(self.ADMIN_USER, self.ADMIN_PASS),
            timeout=10
        )
        if check_response.status_code == 200:
            return True
        if check_response.status_code == 404:
            return False

    def create_vhost(self, username):
        vhost_name = f"{username}_vhost"

        create_vhost_response = requests.put(
            f"{self.RABBITMQ_API_URL}/vhosts/{vhost_name}",
            auth=HTTPBasicAuth(self.ADMIN_USER, self.ADMIN_PASS),
            timeout=10
        )

        if create_vhost_response.status_code in [201, 204]:
            print(f"Vhost '{vhost_name}' created successfully.")
            return vhost_name
        elif create_vhost_response.status_code == 400:
            print(f"Bad request while creating vhost: {create_vhost_response.text}")
            raise ValueError("Bad request during vhost creation")
        else:
            print(f"Unexpected response while creating vhost: {create_vhost_response.status_code} - {create_vhost_response.text}")
            raise ValueError("Unexpected response during vhost creation")

    def delete_vhost(self, vhost_name):
        delete_response = requests.delete(
            f"{self.RABBITMQ_API_URL}/vhosts/{vhost_name}",
            auth=HTTPBasicAuth(self.ADMIN_USER, self.ADMIN_PASS),
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
        username = self.client["name"]
        password = generate_secure_password(self.passowrdlength)

        if self.account_exist(username):
            print(f"User '{username}' already exists. No action performed.")
            raise KeyError("account with this username already exists")
        else:
            self.VHOST = self.create_vhost(username)
            create_response = requests.put(
                f"{self.RABBITMQ_API_URL}/users/{username}",
                auth=HTTPBasicAuth(self.ADMIN_USER, self.ADMIN_PASS),
                json={
                    "password": password,
                    "tags": self.tags
                },
                timeout=10
            )

            if create_response.status_code == 201:
                print(f"User '{username}' created successfully.")
            elif create_response.status_code == 400:
                print(f"Bad Request in the way to rabbitMQ: {create_response.text}")
                raise ValueError("Bad request")
            else:
                print(f"Unexpected response: {create_response.status_code} - {create_response.text}")
                raise ValueError("Unexpected response")
     
            permissions_response = requests.put(
                f"{self.RABBITMQ_API_URL}/permissions/{self.VHOST}/{username}",
                auth=HTTPBasicAuth(self.ADMIN_USER, self.ADMIN_PASS),
                json={
                    "configure": "",  
                    "write": ".*",    
                    "read": ""        
                },
                timeout=10
            )
            return (username, password, self.VHOST)
            
    def remove_account(self):
        username = self.client["name"]
        delete_response = requests.delete(
            f"{self.RABBITMQ_API_URL}/users/{username}",
            auth=HTTPBasicAuth(self.ADMIN_USER, self.ADMIN_PASS),
            timeout=10
        )

        if delete_response.status_code == 204:
            self.delete_vhost(self.VHOST)
            print(f"User '{username}' deleted successfully.")
        elif delete_response.status_code == 404:
            print(f"User '{username}' not found in RabbitMQ.")
            raise KeyError("User not found in RabbitMQ")
        else:
            print(f"Unexpected response: {delete_response.status_code} - {delete_response.text}")
            raise ValueError("Unexpected response")

    def add_queue(self, queue_name: str, queue_type: queue_type):
        username = self.client["name"]
        queue_name = f"{username}.{queue_name}.{queue_type.name}"  

        create_queue_response = requests.put(
            f"{self.RABBITMQ_API_URL}/queues/{self.VHOST}/{queue_name}",
            auth=HTTPBasicAuth(self.ADMIN_USER, self.ADMIN_PASS),
            json={
                "durable": True
            },
            timeout=10
        )

        if create_queue_response.status_code == 201 or create_queue_response.status_code == 204:
            print(f"Queue '{queue_name}' created successfully.")
            return queue_name
        elif create_queue_response.status_code == 400:
            print(f"Bad request while creating queue: {create_queue_response.text}")
            raise ValueError("Bad request during queue creation")
        else:
            print(f"Unexpected response while creating queue: {create_queue_response.status_code} - {create_queue_response.text}")
            raise ValueError("Unexpected response during queue creation")
        
    def remove_queue(self, type: queue_type):
        pass

