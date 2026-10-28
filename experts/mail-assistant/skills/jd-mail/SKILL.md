---
name: jd-mail
description: 使用本机已安装的京Me邮件能力，读取、搜索、总结、分类和整理企业邮箱，并在用户确认后收发邮件。
version: 0.1.0
author: hanzhichao7
---

# 企业邮件操作

`<SKILL_ROOT>` 是本文件所在目录，执行前替换为实际绝对路径。统一入口为 `python3 "<SKILL_ROOT>/scripts/mail.py"`。先执行 `--help` 检查本机技能和 Python 依赖；子命令参数以对应 `--help` 为准。

## 接入方式

适配入口默认加载本机 `~/.joyclaw/remoteSkills/CLAW_SKILL_100016920/scripts/soap_mail_cli.py`，可通过 `JD_MAIL_SKILL_DIR` 指定包含 `scripts/` 的其他安装目录。本包不捆绑内部实现。沿用其现有京Me/SSO 登录逻辑：可用的环境凭据、现有本机登录配置及邮件令牌；不读取 Outlook 密码，不提供账密直连，不自动安装软件。

京Me已登录不代表 DSH 自动继承其登录态。原技能优先读取 `SSO_TOKEN`，其次读取其支持的本机登录配置；也支持现有邮件令牌环境变量。通过本机安全环境配置凭据，不在聊天、专家正文或命令行参数中传递。缺失时会返回 `AUTH_MISSING`，停止查询；令牌过期则按企业登录流程刷新。DSH 需要被允许执行 Python、读取该安装目录与登录配置，并访问企业内网。运行所需 Python 依赖沿用原技能，通常至少需要 `requests`。令牌缓存默认独立放在 `$DSH_HOME/mail-assistant/token.json`，未设置 DSH_HOME 时为 `~/.dsh/mail-assistant/token.json`，新目录与文件使用私有权限。缓存、配置和邮箱数据均不提交 Git。

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
