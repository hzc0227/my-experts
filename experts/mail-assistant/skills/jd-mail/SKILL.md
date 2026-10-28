---
name: jd-mail
description: 使用本机已安装的京Me邮件能力，读取、搜索、总结、分类和整理企业邮箱，并在用户确认后收发邮件。
version: 0.1.1
author: hanzhichao7
---

# 企业邮件操作

`<SKILL_ROOT>` 是本文件所在目录，执行前替换为实际绝对路径。统一入口为 `python3 "<SKILL_ROOT>/scripts/mail.py"`。先执行 `--help` 检查本机技能和 Python 依赖；子命令参数以对应 `--help` 为准。

## 接入方式

适配入口默认加载本机 `~/.joyclaw/remoteSkills/CLAW_SKILL_100016920/scripts/soap_mail_cli.py`，可通过 `JD_MAIL_SKILL_DIR` 指定包含 `scripts/` 的其他安装目录。本包不捆绑内部实现。沿用其现有京Me/SSO 登录逻辑：可用的环境凭据、现有本机登录配置及邮件令牌；不读取 Outlook 密码，不提供账密直连，不自动安装软件。

## 登录与 Token

适配层先复用原技能的有效邮件 Token 或原生 SSO 来源；不可用时，自动从本机 `joyme-bridge` SDK 获取匹配 `joymail-skill.jd.com` 的 `sso.jd.com` Cookie，再调用原技能的登录接口换取邮件 Token。缓存和到期判断由原技能完成，网关鉴权失败时沿用原技能的刷新逻辑。不会把 `me_token` 当成 `sso.jd.com` Cookie 使用。

SDK 默认从 `~/.codex/skills/joyme-bridge`、`~/.agents/skills/joyme-bridge` 查找；其他位置通过 `JOYME_BRIDGE_DIR` 指定。缺少有效登录态时执行：

```bash
python3 "<SKILL_ROOT>/scripts/mail.py" login
# 若提示浏览器已打开，等待用户完成企业登录，然后执行：
python3 "<SKILL_ROOT>/scripts/mail.py" login-finish
```

`login` 使用 SDK 的缓存、静默刷新及必要时的浏览器交互登录；`login-finish` 收尾已挂起的浏览器登录，再换取邮件 Token。成功仅返回鉴权状态，不输出 Cookie 或 Token。普通查询不会自动启动交互式扫码；缺失凭据时提示执行登录命令。

DSH 需要允许执行 Python、读取原技能与登录 SDK，并访问企业网络。邮件脚本通常至少需要 `requests`，交互登录的浏览器依赖由本机 SDK 管理。邮件 Token 默认独立缓存于 `$DSH_HOME/mail-assistant/token.json`，未设置 DSH_HOME 时为 `~/.dsh/mail-assistant/token.json`，新目录与文件使用私有权限。缓存、配置和邮箱数据均不提交 Git。写操作预览不会触发获取登录态或换取 Token。


## 查询

```bash
python3 "<SKILL_ROOT>/scripts/mail.py" folders
python3 "<SKILL_ROOT>/scripts/mail.py" search --folder inbox --unread --limit 20 --format json
python3 "<SKILL_ROOT>/scripts/mail.py" detail --item-id "<查询返回的ID>" --format json
python3 "<SKILL_ROOT>/scripts/mail.py" pending-important --days 7 --format json
python3 "<SKILL_ROOT>/scripts/mail.py" lookup-recipient --condition "<ERP或姓名>" --format json
```

默认最近一天；用户指定范围时传 `--after` / `--before` 或相应 `--days`。搜索包含客户端过滤、分页和扫描上限，必须检查实际返回规模与完整性；无结果不等于整个邮箱不存在。`summarize` 只将标准输入 JSON 转为摘要，不访问邮箱。

## 写入预览与执行

以下仅是参数示例，不能作为发送授权：

```bash
python3 "<SKILL_ROOT>/scripts/mail.py" send --to "<用户确认的邮箱>" --subject "<主题>" --body "<正文>"
python3 "<SKILL_ROOT>/scripts/mail.py" batch-move --item-ids "<ID1>,<ID2>" --target-folder-id "<目标ID>"
python3 "<SKILL_ROOT>/scripts/mail.py" create-folder --display-name "<名称>"
```

不带 `--confirm` 的写操作只返回参数预览，不登录、不发网关请求。展示预览并取得用户确认后，原命令加 `--confirm` 才执行；参数标志是脚本执行门槛，不代替用户授权。适配层拒绝未列入允许列表的新命令，后台技能升级后需先审核能力再更新适配层。

支持 `send`、`reply`、`forward`、`create-folder`、`batch-mark-read`、`batch-mark-unread`、`batch-add-category`、`batch-move`、`batch-delete`、`flag`、`unflag`、`batch-flag`、`batch-unflag`。删除仅允许 `MoveToDeletedItems` 软删除，永久删除在预览和执行时都拒绝。

先用 `folders` 和 `detail` 确认文件夹及邮件对象。执行后回读受影响对象；移动后 ID 可能变化，重新查询，不盲用旧 ID。不要直接运行原始脚本绕过适配入口。查询失败时不继续推导分类结果或执行写操作。
