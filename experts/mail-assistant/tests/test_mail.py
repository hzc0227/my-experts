"""Offline regression tests for write dispatch. @Author hanzhichao7."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).parents[1] / "skills/jd-mail/scripts"))
spec = importlib.util.spec_from_file_location(
    "mail_adapter", Path(__file__).parents[1] / "skills/jd-mail/scripts/mail.py"
)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class MailDispatchTests(unittest.TestCase):
    """Check side effects using a backend that only records handler calls."""

    def setUp(self):
        """Create fake parsers without credentials, imports or network requests."""
        self.calls = []

        def build_parser():
            """Expose all known writes plus an unreviewed future operation."""
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            for name in adapter.READ_COMMANDS | adapter.WRITE_COMMANDS | {"future-write"}:
                child = sub.add_parser(name)
                if name == "batch-delete":
                    child.add_argument("--delete-type", default="MoveToDeletedItems")
                child.set_defaults(func=lambda args: self.calls.append(args.command))
            return parser

        self.backend = SimpleNamespace(build_parser=build_parser)

    def test_every_write_previews_without_running_handler(self):
        """Even sending and folder creation must stop before backend execution."""
        for name in adapter.WRITE_COMMANDS:
            with self.subTest(command=name), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(adapter.execute(self.backend, [name]), 0)
                self.assertFalse(json.loads(output.getvalue())["executed"])
        self.assertEqual(self.calls, [])

    def test_write_preview_never_acquires_credentials(self):
        """Preparing a write cannot open login or obtain a mail token."""
        def unexpected_login():
            """Fail if preview reaches the authentication callback."""
            self.fail("preview attempted authentication")

        with redirect_stdout(io.StringIO()):
            adapter.execute(self.backend, ["send"], unexpected_login)

    def test_explicit_confirmation_dispatches_each_write_once(self):
        """Confirmation enables exactly the reviewed operation requested."""
        for name in sorted(adapter.WRITE_COMMANDS):
            adapter.execute(self.backend, [name, "--confirm"])
        self.assertEqual(self.calls, sorted(adapter.WRITE_COMMANDS))

    def test_reads_execute_directly(self):
        """Queries retain the backend's normal execution path."""
        adapter.execute(self.backend, ["folders"])
        self.assertEqual(self.calls, ["folders"])

    def test_unknown_operation_cannot_bypass_review(self):
        """A newly added backend command remains disabled in the adapter."""
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            adapter.execute(self.backend, ["future-write"])
        self.assertEqual(self.calls, [])

    def test_hard_delete_rejected_in_preview_and_execution(self):
        """A confirmation flag does not grant permanent deletion support."""
        for suffix in [[], ["--confirm"]]:
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                adapter.execute(self.backend, [
                    "batch-delete", "--delete-type", "HardDelete", *suffix,
                ])
        self.assertEqual(self.calls, [])

    def test_missing_login_returns_actionable_error_without_secret(self):
        """Missing credentials are reported without exposing backend error data."""
        def build_parser():
            """Fail the read handler as the installed backend does without SSO."""
            parser = self.backend.build_parser()

            def missing_login(args):
                """Include a sentinel to catch accidental raw error output."""
                raise RuntimeError("unable to resolve sso_token SECRET_SENTINEL")

            parser.set_defaults(func=missing_login)
            for action in parser._actions:
                if isinstance(action, argparse._SubParsersAction):
                    action.choices["folders"].set_defaults(func=missing_login)
            return parser

        with tempfile.TemporaryDirectory() as temp:
            skill = Path(temp) / "installed"
            (skill / "scripts").mkdir(parents=True)
            (skill / "scripts/soap_mail_cli.py").touch()
            fake = SimpleNamespace(build_parser=build_parser)
            with patch.dict(os.environ, {
                "JD_MAIL_SKILL_DIR": str(skill), "DSH_HOME": temp,
            }), patch.object(adapter.importlib, "import_module", return_value=fake), \
                    patch.object(adapter, "acquire_mail_token", side_effect=RuntimeError(
                        "unable to resolve sso_token SECRET_SENTINEL"
                    )), \
                    redirect_stdout(io.StringIO()) as output:
                self.assertEqual(adapter.main(["folders"]), 1)
            result = json.loads(output.getvalue())
            self.assertEqual(result["error_code"], "AUTH_MISSING")
            self.assertNotIn("SECRET_SENTINEL", output.getvalue())


if __name__ == "__main__":
    unittest.main()
