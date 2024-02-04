import logging

from webapi.session import AuthenticatedSession

logger = logging.getLogger(__name__)


def authenticator(credential: dict) -> str:
    logger.debug("credential = %s", credential)
    return "DUMMY_AUTHORIZATION_TOKEN"


def credential_applier(session: AuthenticatedSession, headers: dict[str, str], body: str) -> tuple[dict[str, str], str]:
    logger.debug("headers = %s", headers)
    logger.debug("body = %s", body)

    headers.update({"Authorization": "Bearer " + session.auth_token})

    return headers, body
