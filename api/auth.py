from api.base import BaseClient


class AuthClient(BaseClient):
    TOKEN_PATH = "/token"

    def get_token(self, username: str, password: str) -> dict:
        response = self.post(
            self.TOKEN_PATH,
            data={
                "grant_type": "password",
                "username": username,
                "password": password,
            },
        )
        response.raise_for_status()
        return response.json()
