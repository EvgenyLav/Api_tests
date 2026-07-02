import allure
import pytest

from tests.helpers import attach_text


@allure.feature("Auth API")
@allure.story("Token smoke")
@pytest.mark.smoke
@pytest.mark.auth
def test_get_token(token_data):
    assert token_data.access_token, "access_token пустой"
    assert token_data.token_type == "bearer"
    assert token_data.expires_in is not None and token_data.expires_in > 0, "expires_in некорректный"
    attach_text(token_data.token_type, "token_type")
    attach_text(token_data.expires_in, "expires_in")
