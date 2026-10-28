"""Acquire enterprise mail credentials via a local bridge. @Author hanzhichao7."""

import importlib
import os
from pathlib import Path
import sys


class LoginRequiredError(RuntimeError):
    """No reusable SSO session exists; interactive login is required."""


def load_bridge():
    """Load the installed login SDK without copying its implementation or secrets.

    JOYME_BRIDGE_DIR selects its skill root. Default discovery checks the two
    local skill locations; absence is reported before any browser is opened.
    """
    configured = os.environ.get("JOYME_BRIDGE_DIR")
    roots = [Path(configured).expanduser()] if configured else [
        Path.home() / ".codex/skills/joyme-bridge",
        Path.home() / ".agents/skills/joyme-bridge",
    ]
    for root in roots:
        scripts = root / "scripts"
        if (scripts / "_gateway.py").is_file():
            sys.path.insert(0, str(scripts.resolve()))
            return importlib.import_module("_gateway")
    raise LoginRequiredError("install joyme-bridge or configure JOYME_BRIDGE_DIR")


def acquire_mail_token(mail, *, login: str = "") -> str:
    """Reuse mail credentials, then exchange a domain-matched SSO cookie.

    Normal requests first use the backend's explicit token, private cache and
    native SSO sources. On authentication failure, bridge cookies are consulted
    without launching interactive login. Explicit login delegates session
    acquisition to the SDK; login-finish completes a previously opened browser.
    Only the sso.jd.com cookie for the login host is forwarded as SSO_TOKEN;
    a me_token is never substituted for it. Token persistence, expiry and
    authenticated gateway refresh remain owned by the existing mail backend.
    The returned secret is for in-process use only, never console output.
    """
    if not login:
        try:
            return mail.get_valid_auth_token()
        except mail.SoapMailError:
            pass
    bridge = load_bridge()
    if login == "login":
        bridge.get_me_token()
    elif login == "login-finish":
        bridge.finish_pending_login()
    cookies = bridge.load_cookies_for("joymail-skill.jd.com", ensure=["sso.jd.com"])
    sso = cookies.get("sso.jd.com")
    if not sso:
        raise LoginRequiredError("run mail.py login, then login-finish if requested")
    os.environ["SSO_TOKEN"] = sso
    return mail.get_valid_auth_token(force_refresh=True)
