import requests


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
