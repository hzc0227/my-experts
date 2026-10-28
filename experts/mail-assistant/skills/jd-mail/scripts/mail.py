#!/usr/bin/env python3
"""DSH adapter for an installed enterprise mail skill. @Author hanzhichao7."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import sys

from mail_auth import LoginRequiredError, acquire_mail_token


READ_COMMANDS = frozenset({
    "folders", "search", "detail", "daily-stats", "pending-important",
    "person-unhandled", "lookup-recipient", "summarize",
})
WRITE_COMMANDS = frozenset({
    "send", "reply", "forward", "create-folder", "batch-mark-read",
    "batch-mark-unread", "batch-add-category", "batch-move", "batch-delete",
    "flag", "unflag", "batch-flag", "batch-unflag",
})


def execute(backend, argv: list[str], authenticate=None) -> int:
    """Parse using the installed CLI and dispatch only reviewed commands.

    Writes without --confirm return the exact parsed parameters before any
    handler or authentication runs. Confirmation must come from the user;
    the flag only prevents accidental execution. Unknown commands and hard
    deletion are rejected even when the flag is present. Returns the process
    exit status; backend results retain their existing output format.
    """
    parser = backend.build_parser()
    parser.epilog = "Authentication: mail.py login | mail.py login-finish"
    subcommands = next(
        action for action in parser._actions if hasattr(action, "choices")
        and isinstance(action.choices, dict)
    ).choices
    for command in WRITE_COMMANDS:
        if command in subcommands:
            subcommands[command].add_argument(
                "--confirm", action="store_true", help="execute after user confirmation"
            )
    args = parser.parse_args(argv)
    if args.command not in READ_COMMANDS | WRITE_COMMANDS:
        parser.error("command has not been reviewed for this adapter")
    if args.command == "batch-delete" and args.delete_type != "MoveToDeletedItems":
        parser.error("only MoveToDeletedItems soft deletion is supported")
    if args.command in WRITE_COMMANDS and not args.confirm:
        parameters = {
            key: value for key, value in vars(args).items()
            if key not in {"func", "confirm", "command", "endpoint", "debug"}
        }
        print(json.dumps({
            "success": True, "mode": "preview", "executed": False,
            "command": args.command, "parameters": parameters,
        }, ensure_ascii=False))
        return 0
    if authenticate is not None and args.command != "summarize":
        authenticate()
    args.func(args)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Load local backend code and keep credentials outside the expert library.

    JD_MAIL_SKILL_DIR selects an already installed, trusted skill directory.
    Private creation permissions cover the independent token cache; existing
    credential configuration and mail-token refresh remain backend-owned; the
    login adapter supplies a bridge SSO session when native sources fail.
    Dependency or connection failures return a redacted error without dumping
    tokens or server responses into the conversation. No package is installed.
    """
    skill = Path(os.environ.get(
        "JD_MAIL_SKILL_DIR", "~/.joyclaw/remoteSkills/CLAW_SKILL_100016920"
    )).expanduser()
    scripts = skill / "scripts"
    if not (scripts / "soap_mail_cli.py").is_file():
        print(json.dumps({"success": False, "error":
            "未找到本机邮件技能，请安装原技能或配置 JD_MAIL_SKILL_DIR。"}, ensure_ascii=False))
        return 1
    previous_umask = os.umask(0o077)
    try:
        cache = Path(os.environ.get("DSH_HOME", "~/.dsh")).expanduser() / "mail-assistant"
        cache.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MAIL_TOKEN_CACHE_PATH", str(cache / "token.json"))
        sys.path.insert(0, str(scripts.resolve()))
        backend = importlib.import_module("soap_mail_cli")
        mail = importlib.import_module("soap_mail")
        arguments = sys.argv[1:] if argv is None else argv
        if arguments and arguments[0] in {"login", "login-finish"}:
            if len(arguments) != 1:
                raise ValueError("login commands accept no additional arguments")
            acquire_mail_token(mail, login=arguments[0])
            print(json.dumps({"success": True, "authenticated": True}, ensure_ascii=False))
            return 0
        return execute(backend, arguments, lambda: acquire_mail_token(mail))
    except Exception as error:
        pending = type(error).__name__ == "PendingLoginError"
        missing_auth = isinstance(error, LoginRequiredError) or "unable to resolve sso_token" in str(error)
        print(json.dumps({
            "success": False, "error_type": type(error).__name__,
            "error_code": "AUTH_LOGIN_PENDING" if pending else "AUTH_MISSING" if missing_auth else "BACKEND_FAILED",
            "error": (
                "浏览器已打开，请完成企业登录后执行 mail.py login-finish。"
                if pending else
                "缺少可用登录态；请安装 joyme-bridge 或配置 JOYME_BRIDGE_DIR，然后执行 mail.py login。"
                if missing_auth else
                "邮件操作未完成；请检查 Python 依赖、京Me/SSO 登录态及企业网络。写操作结果不明时先回读邮箱，勿直接重试。"
            ),
        }, ensure_ascii=False))
        return 1
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
