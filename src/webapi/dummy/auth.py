import logging

from webapi.session import AuthenticatedSession

logger = logging.getLogger(__name__)


def authenticator(credential: dict) -> str:
    """認証する。

    Returns:
        認証トークン
    """
    logger.debug("credential = %s", credential)
    return "DUMMY_AUTHORIZATION_TOKEN"


def credential_applier(session: AuthenticatedSession,
                       headers: dict[str, str],
                       body: dict) -> tuple[dict[str, str], dict]:
    """認証情報を適用する。

    Returns:
        認証情報を適用したヘッダとボディ
    """
    headers.update({"Authorization": "Bearer " + session.auth_token})

    logger.debug("headers = %s", headers)
    logger.debug("body = %s", body)

    return headers, body
