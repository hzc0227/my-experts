"""Offline session acquisition checks. @Author hanzhichao7."""

import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parents[1] / "skills/jd-mail/scripts"))
import mail_auth


class AuthTests(unittest.TestCase):
    """Distinguish mail credentials, domain cookies and interactive login."""

    def setUp(self):
        """Build isolated providers without reading real cookies or the network."""
        self.mail = SimpleNamespace(SoapMailError=ValueError, get_valid_auth_token=Mock())
        self.bridge = SimpleNamespace(
            load_cookies_for=Mock(return_value={"sso.jd.com": "SSO_SENTINEL"}),
            get_me_token=Mock(), finish_pending_login=Mock(),
        )

    def test_valid_mail_token_skips_bridge(self):
        """An existing usable token needs no new login or browser session."""
        self.mail.get_valid_auth_token.return_value = "MAIL_SENTINEL"
        with patch.object(mail_auth, "load_bridge") as load:
            self.assertEqual(mail_auth.acquire_mail_token(self.mail), "MAIL_SENTINEL")
            load.assert_not_called()

    def test_bridge_sso_is_exchanged_after_native_auth_fails(self):
        """Only a domain-matched SSO cookie is forwarded for mail-token exchange."""
        self.mail.get_valid_auth_token.side_effect = [ValueError("expired"), "MAIL_SENTINEL"]
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(mail_auth, "load_bridge", return_value=self.bridge):
            self.assertEqual(mail_auth.acquire_mail_token(self.mail), "MAIL_SENTINEL")
            self.assertEqual(os.environ["SSO_TOKEN"], "SSO_SENTINEL")
        self.bridge.load_cookies_for.assert_called_once_with(
            "joymail-skill.jd.com", ensure=["sso.jd.com"]
        )
        self.mail.get_valid_auth_token.assert_called_with(force_refresh=True)
        self.bridge.get_me_token.assert_not_called()

    def test_me_token_cannot_substitute_for_sso_cookie(self):
        """Missing SSO stops the operation instead of exchanging the wrong token."""
        self.mail.get_valid_auth_token.side_effect = ValueError("missing")
        self.bridge.load_cookies_for.return_value = {"me_token": "WRONG_SENTINEL"}
        with patch.object(mail_auth, "load_bridge", return_value=self.bridge), \
                self.assertRaises(mail_auth.LoginRequiredError):
            mail_auth.acquire_mail_token(self.mail)
        self.assertEqual(self.mail.get_valid_auth_token.call_count, 1)

    def test_explicit_login_and_finish_use_their_sdk_flows(self):
        """Both interactive entry and browser completion then exchange a mail token."""
        for command, callback in [("login", "get_me_token"), ("login-finish", "finish_pending_login")]:
            with self.subTest(command=command), patch.dict(os.environ, {}, clear=True), \
                    patch.object(mail_auth, "load_bridge", return_value=self.bridge):
                mail_auth.acquire_mail_token(self.mail, login=command)
                getattr(self.bridge, callback).assert_called_once()
        self.assertEqual(self.mail.get_valid_auth_token.call_count, 2)


if __name__ == "__main__":
    unittest.main()
