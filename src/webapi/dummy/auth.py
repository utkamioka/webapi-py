from __future__ import annotations

import logging

from ..session import AuthenticatedSession

logger = logging.getLogger(__name__)


def authenticator(credential: dict) -> str:
    """認証する。

    Returns:
        認証トークン
    """
    # 認証情報のロギングはしない方が望ましい
    logger.debug("credential = %s", credential)

    # credentialに含まれる認証情報を元にアクセストークンを取得
    return "DUMMY_AUTHORIZATION_TOKEN"


def credential_applier(
    session: AuthenticatedSession, headers: dict[str, str], body: dict | list | None
) -> tuple[dict[str, str], dict]:
    """認証情報を適用する。

    Returns:
        認証情報を適用したヘッダとボディ
    """
    headers.update({"Authorization": "Bearer " + session.auth_token})

    # アクセストークンを含むヘッダのロギングはしない方が望ましい
    logger.debug("headers = %s", headers)
    logger.debug("body = %s", body)

    return headers, body
