# 我的专家库

适用于 `@weibaohui/experts-management` 的个人专家源。作者：hanzhichao7。

## 接入 DSH

在「专家管理 → 内置 → 内置设置」中配置：

- 仓库地址：`https://github.com/hzc0227/my-experts.git`
- 分支：`main`
- 保持默认稀疏检出目录 `experts`，保存后手动同步。

同步后可以浏览专家；安装到「我的」后，通过 `/expert-general-assistant` 使用通用助手。

## 目录结构

```text
experts/
└── general-assistant/
    ├── .codebuddy-plugin/plugin.json
    └── agents/general-assistant.md
```

## 新增专家

1. 复制 `experts/general-assistant/`，目录名使用小写英文和连字符。
2. 修改 `plugin.json` 的 `name`、展示名称、职业和描述。
3. 重命名角色文件，同步修改 `agents` 路径、`agentName` 及角色文件的 frontmatter。
4. 编写角色职责、执行要求和适用范围，提交到 `main` 后在插件中同步。

关联技能可放在专家自身的 `skills/<技能名>/SKILL.md`，并在 `plugin.json` 的 `skills` 中声明 `./skills/<技能名>`；无关联技能时保持空数组。不要提交凭据、内部业务数据或敏感提示词。

当前包含 1 个单人专家示例和 1 个数据分析专家团。数据分析专家团的能力与运行限制见 [说明](experts/data-analysis/README.md)。
