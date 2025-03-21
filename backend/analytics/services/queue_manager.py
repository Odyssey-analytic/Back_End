from .queue_type import queue_type
import requests
from requests.auth import HTTPBasicAuth
from .Utilities import generate_secure_password

class RabbitAccountManager:
    def __init__(self):
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

    def create_account(self, client):
        username = client["name"]
        password = generate_secure_password(self.passowrdlength)

        if self.account_exist(username):
            print(f"User '{username}' already exists. No update performed.")
        else:
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
                return (username, password)
            elif create_response.status_code == 400:
                print(f"Bad Request: {create_response.text}")
            else:
                print(f"Unexpected response: {create_response.status_code} - {create_response.text}")
            
    def delete_account(client):
        pass

    def add_queue(client, type: queue_type):
        pass

    def remove_queue(client, type: queue_type):
        pass

    def remove_account(client):
        pass
