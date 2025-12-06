# Python imports
import os
import logging

# Module imports
from plane.authentication.adapter.credential import CredentialAdapter
from plane.db.models import User
from plane.authentication.adapter.error import (
    AUTHENTICATION_ERROR_CODES,
    AuthenticationException,
)
from plane.license.utils.instance_value import get_configuration_value

logger = logging.getLogger(__name__)

# LDAP Configuration - loaded from environment
LDAP_ENABLED = os.environ.get("LDAP_ENABLED", "1") == "1"
LDAP_SERVER = os.environ.get("LDAP_SERVER", "192.168.20.5")
LDAP_PORT = int(os.environ.get("LDAP_PORT", "389"))
LDAP_DOMAIN = os.environ.get("LDAP_DOMAIN", "cslog.local")


def verify_ldap_password(email: str, password: str) -> bool:
    """
    Verify user credentials against LDAP/Active Directory.
    Returns True if authentication successful, False otherwise.
    """
    if not LDAP_ENABLED:
        return False

    try:
        from ldap3 import Server, Connection, ALL

        username = email.split("@")[0]
        server = Server(LDAP_SERVER, port=LDAP_PORT, get_info=ALL)

        # Try UPN format (user@domain)
        try:
            conn = Connection(
                server,
                user=f"{username}@{LDAP_DOMAIN}",
                password=password,
                auto_bind=True
            )
            conn.unbind()
            logger.info(f"LDAP auth successful for {email}")
            return True
        except Exception:
            pass

        # Try DOMAIN\user format
        try:
            domain_short = LDAP_DOMAIN.split(".")[0].upper()
            conn = Connection(
                server,
                user=f"{domain_short}\\{username}",
                password=password,
                auto_bind=True
            )
            conn.unbind()
            logger.info(f"LDAP auth successful for {email}")
            return True
        except Exception:
            pass

        logger.warning(f"LDAP auth failed for {email}")
        return False

    except ImportError:
        logger.error("ldap3 library not installed")
        return False
    except Exception as e:
        logger.error(f"LDAP error for {email}: {e}")
        return False


class EmailProvider(CredentialAdapter):
    provider = "email"

    def __init__(self, request, key=None, code=None, is_signup=False, callback=None):
        super().__init__(request=request, provider=self.provider, callback=callback)
        self.key = key
        self.code = code
        self.is_signup = is_signup

        (ENABLE_EMAIL_PASSWORD,) = get_configuration_value(
            [
                {
                    "key": "ENABLE_EMAIL_PASSWORD",
                    "default": os.environ.get("ENABLE_EMAIL_PASSWORD"),
                }
            ]
        )

        if ENABLE_EMAIL_PASSWORD == "0":
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["EMAIL_PASSWORD_AUTHENTICATION_DISABLED"],
                error_message="EMAIL_PASSWORD_AUTHENTICATION_DISABLED",
            )

    def set_user_data(self):
        if self.is_signup:
            # Check if the user already exists
            if User.objects.filter(email=self.key).exists():
                raise AuthenticationException(
                    error_message="USER_ALREADY_EXIST",
                    error_code=AUTHENTICATION_ERROR_CODES["USER_ALREADY_EXIST"],
                )

            super().set_user_data(
                {
                    "email": self.key,
                    "user": {
                        "avatar": "",
                        "first_name": "",
                        "last_name": "",
                        "provider_id": "",
                        "is_password_autoset": False,
                    },
                }
            )
            return
        else:
            user = User.objects.filter(email=self.key).first()

            # User does not exists
            if not user:
                raise AuthenticationException(
                    error_message="USER_DOES_NOT_EXIST",
                    error_code=AUTHENTICATION_ERROR_CODES["USER_DOES_NOT_EXIST"],
                    payload={"email": self.key},
                )

            # ===========================================
            # MODIFIED: Check LDAP first, then fall back to local password
            # ===========================================
            auth_success = False

            # Try LDAP authentication first
            if LDAP_ENABLED:
                auth_success = verify_ldap_password(self.key, self.code)

            # Fall back to local password if LDAP fails or is disabled
            if not auth_success:
                auth_success = user.check_password(self.code)

            if not auth_success:
                raise AuthenticationException(
                    error_message=(
                        "AUTHENTICATION_FAILED_SIGN_UP" if self.is_signup else "AUTHENTICATION_FAILED_SIGN_IN"
                    ),
                    error_code=AUTHENTICATION_ERROR_CODES[
                        ("AUTHENTICATION_FAILED_SIGN_UP" if self.is_signup else "AUTHENTICATION_FAILED_SIGN_IN")
                    ],
                    payload={"email": self.key},
                )

            super().set_user_data(
                {
                    "email": self.key,
                    "user": {
                        "avatar": "",
                        "first_name": "",
                        "last_name": "",
                        "provider_id": "",
                        "is_password_autoset": False,
                    },
                }
            )
            return
