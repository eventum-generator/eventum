"""Shared HTTP Basic-auth credential verification."""

import base64
import secrets


def verify_basic_credentials(
    encoded: str,
    expected_user: str,
    expected_password: str,
) -> str | None:
    """Return the username if the Basic credentials match, else None.

    Decodes the base64 ``user:password`` portion of a Basic
    Authorization header (the token after the ``Basic`` scheme) and
    compares both parts against the expected credentials in constant
    time. Both comparisons always run, so the result does not reveal
    through timing whether only the username was correct.

    Parameters
    ----------
    encoded : str
        Base64-encoded ``user:password`` token.

    expected_user : str
        Expected username.

    expected_password : str
        Expected password.

    Returns
    -------
    str | None
        The authenticated username on a match, or None if the token is
        malformed or the credentials do not match.

    """
    try:
        user, _, password = base64.b64decode(encoded).decode().partition(':')
    except ValueError:
        return None

    # Compare as bytes: secrets.compare_digest raises TypeError on a
    # non-ASCII str, which crafted credentials could contain.
    user_ok = secrets.compare_digest(user.encode(), expected_user.encode())
    password_ok = secrets.compare_digest(
        password.encode(), expected_password.encode()
    )
    return user if (user_ok and password_ok) else None
