from __future__ import annotations

import logging

from ..credentials import AuthenticatedCredentials, Credentials

logger = logging.getLogger(__name__)


def authenticator(credential: Credentials) -> str:
    """認証する。

    Returns:
        アクセストークン
    """
    # 認証情報のロギングはしない方が望ましい
    logger.debug("credential = %s", credential)

    # credentialに含まれる認証情報を元にアクセストークンを取得
    return "DUMMY_AUTHORIZATION_TOKEN"


def credential_applier(credentials: AuthenticatedCredentials, headers: dict[str, str]) -> dict[str, str]:
    """リクエストヘッダにアクセストークンを適用する。

    Returns:
        アクセストークンを適用したリクエストヘッダ
    """
    headers.update({"Authorization": "Bearer " + credentials.access_token})

    # アクセストークンを含むヘッダのロギングはしない方が望ましい
    logger.debug("headers = %s", headers)

    return headers
