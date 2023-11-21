import configparser
import os
import random
import threading

import requests
from faker import Faker


class UserClientBot:

    base_url = 'http://0.0.0.0:8000/api'
    base_auth_header = 'Bearer'

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self._created_posts_ids = set()

    @property
    def auth_header(self):
        return f'{self.base_auth_header} {self.access_token}'

    @property
    def created_posts_ids(self):
        return self._created_posts_ids

    def signup(self):
        data = {
            'username': self.username,
            'password': self.password,
            'password2': self.password

        }
        response = requests.post(f'{self.base_url}/users/signup/', json=data)
        response.raise_for_status()
        return response

    def login(self):
        data = {
            'username': self.username,
            'password': self.password
        }
        response = requests.post(f'{self.base_url}/users/login/', json=data)
        response.raise_for_status()
        tokens = response.json()
        self._update_tokens(access_token=tokens.get('access'), refresh_token=tokens.get('refresh'))

    def logout(self):
        data = {
            'refresh': self.refresh_token
        }
        response = requests.post(f'{self.base_url}/users/logout/', json=data,
                                 headers={'Authorization': self.auth_header})
        response.raise_for_status()

    def _update_tokens(self, access_token, refresh_token=None):
        if access_token:
            self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token

    def token_refresh(self):
        data = {'refresh': self.refresh_token}
        response = requests.post(f'{self.base_url}/users/token/refresh', json=data)
        response.raise_for_status()
        self._update_tokens(access_token=response.json().get('access'))
        return response

    def create_post(self, title: str, text: str):
        data = {
            'title': title,
            'text': text
        }
        response = requests.post(f'{self.base_url}/posts/', json=data, headers={'Authorization': self.auth_header})
        response.raise_for_status()
        post_id = response.json().get('id')
        if post_id:
            self._created_posts_ids.add(post_id)

    def like_post(self, post_id):
        response = requests.post(f'{self.base_url}/posts/{post_id}/like/',
                                 headers={'Authorization': self.auth_header})
        response.raise_for_status()


def load_config():
    # Config file parsing
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config['DEFAULT']


def user_flow(max_posts_per_user: int, max_likes_per_user: int, file_path: str, file_lock: threading.Lock,
              barrier: threading.Barrier):

    # User Client Initialisation
    username = fake.user_name()
    password = fake.password()
    client = UserClientBot(username=username, password=password)

    # Basic signup and login in system
    client.signup()
    client.login()

    # Creating Posts
    for _ in range(max_posts_per_user):
        post_title = fake.catch_phrase()
        post_text = fake.paragraph(nb_sentences=3)
        client.create_post(title=post_title, text=post_text)

    # Saving created posts ids to file used as temporary storage across threads
    with file_lock:
        with open(file_path, 'a') as file:
            file.write('\n'.join([str(post_id) for post_id in client.created_posts_ids]) + '\n')

    barrier.wait()

    if barrier.n_waiting == 0:  # When each thread has completed writing post_ids into temp file storage

        with open(file_path, 'r') as file:  # Random choice across created post_ids to be like by user.
            posts_ids = [int(line.strip()) for line in file.readlines()]
            posts_ids_to_be_liked = random.choices(posts_ids, k=max_likes_per_user)
            for post_id in posts_ids_to_be_liked:
                client.like_post(post_id)

    client.logout()


if __name__ == '__main__':

    config_params = load_config()
    number_of_users = int(config_params.get('number_of_users', 1))
    max_posts_per_user = int(config_params.get('max_posts_per_user', 1))
    max_likes_per_user = int(config_params.get('max_likes_per_user', 1))

    threads = []
    file_path = 'temp_db.txt'
    file_lock = threading.Lock()  # Lock for file writing
    barrier = threading.Barrier(number_of_users)  # barrier to synchronize threads

    # Faker initialization
    fake = Faker()

    for _ in range(number_of_users):  # Creating pool of threads equal to user number
        thread = threading.Thread(target=user_flow,
                                  args=(max_posts_per_user, max_likes_per_user, file_path, file_lock, barrier))
        threads.append(thread)
        thread.start()

    for thread in threads:  # join threads to wait until all threads are finished
        thread.join()

    os.remove(file_path)  # Clean file, using as temp db.
