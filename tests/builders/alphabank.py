from utils.constants import LANG_RUS


def build_status_payload(order_id: str) -> dict:
    return {
        "OrderId": order_id,
        "Lang": LANG_RUS,
    }


def build_validation_payload(order_id: str) -> dict:
    return {
        "OrderId": order_id,
        "NotCheckValidation": True,
        "Lang": LANG_RUS,
    }
