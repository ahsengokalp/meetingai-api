from __future__ import annotations

import logging
import re

from meetingai_shared.config import LDAP_HOST, LDAP_PORT, LDAP_USER_DN_FORMAT


logger = logging.getLogger(__name__)

_LDAP_DN_ESCAPE_RE = re.compile(r'([,\\#+<>;"=\x00])')


def _escape_dn_value(value: str) -> str:
    escaped = _LDAP_DN_ESCAPE_RE.sub(r'\\\1', value)
    if escaped.startswith((" ", "#")):
        escaped = "\\" + escaped
    if escaped.endswith(" "):
        escaped = escaped[:-1] + "\\ "
    return escaped


class LdapService:
    @staticmethod
    def authenticate(username: str, password: str) -> dict[str, str] | None:
        try:
            from ldap3 import ALL, Connection, Server

            normalized_username = str(username or "").strip()
            if not normalized_username or not password:
                return None

            if not LDAP_HOST:
                raise RuntimeError("LDAP ayarlari eksik: LDAP_HOST tanimlanmamis.")
            if not LDAP_USER_DN_FORMAT:
                raise RuntimeError("LDAP ayarlari eksik: LDAP_USER_DN_FORMAT tanimlanmamis.")

            safe_username = _escape_dn_value(normalized_username)
            user_dn = LDAP_USER_DN_FORMAT.format(username=safe_username)
            server = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL)

            with Connection(server, user=user_dn, password=password, auto_bind=True) as conn:
                if conn.bound:
                    return {
                        "username": normalized_username,
                        "user_dn": user_dn,
                    }
        except RuntimeError:
            raise
        except Exception as exc:
            logger.warning("LDAP auth error: %s", exc)
        return None
