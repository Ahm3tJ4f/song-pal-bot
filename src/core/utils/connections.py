import secrets
import string


def generate_pair_code(length: int = 5) -> str:
    """
    Generate a random pair code (5 chars, lowercase + digits).
    Case-insensitive matching in validation.
    """
    alphabet = string.ascii_lowercase + string.digits  # a-z, 0-9
    return "".join(secrets.choice(alphabet) for _ in range(length))
