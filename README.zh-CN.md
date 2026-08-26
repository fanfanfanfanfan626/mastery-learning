# Mastery Tutor

**面向 AI Agent 的本地优先掌握式学习导师。**

它把引导式 HTML 课程、动手练习、迁移检验、间隔复习和可检查的学习进度放在同一套工作流里。
学习记录保存在你选择的本地工作区，而不是某个远程账号中。

[English](README.md) · [兼容状态](COMPATIBILITY.md) · [安装说明](INSTALL.md)

![Mastery Tutor 演示](docs/assets/demo.gif)

| AI 宿主 | 当前状态 | 分发形式 |
|---|---|---|
| Codex | **已验证适配器** | 完整插件 |
| Claude Code | 实验性 | 两个 Skill |
| GitHub Copilot | 实验性 | 两个 Skill |
| 通用 Agent Skills 宿主 | 核心兼容 | 两个 Skill |
| OpenCode | 计划中 | 尚未发布 |

“核心兼容”只表示宿主能够发现并安装两个标准 Skill，并不等于该宿主已经通过 HTML 教室、跨会话恢复、
本地服务器清理和卸载等完整测试。每个状态的证据见 [COMPATIBILITY.md](COMPATIBILITY.md)。

## 让 AI 安装

把下面一段交给你的 AI Agent：

```text
请从 https://github.com/fanfanfanfanfan626/mastery-tutor 安装 Mastery Tutor。
先读取 AI_INSTALL.md，识别当前宿主，完整安装两个必需 Skill；
没有通过该宿主的验收步骤前，不要宣称安装成功。发现旧版本先告诉我，不要直接覆盖或删除任何
.mastery 学习数据。若当前宿主是 Codex 且 codex --version 不可用，我允许你仅按 OpenAI 官方
Codex CLI 文档安装或修复正式 CLI；禁止复制 WindowsApps 内部程序、修改其权限、使用
skill-installer 或只安装一个嵌套 Skill。
```

Codex 会安装一个完整的 `mastery-tutor` 插件；其他兼容宿主会安装 `mastery-coach` 和
`mastery-tool-creator`。两者共同组成产品，不能只装其中一个。手动安装和成功条件见
[INSTALL.md](INSTALL.md)。

安装后直接说你的真实目标即可：

```text
帮我从零系统学习机器学习、人工智能和大模型。
我每天能学 40 分钟，数学还可以，希望多用可视化讲解。
```

第一次使用会打开一张紧凑、可跳过的入门教室卡片，把目标、背景、时间和教学偏好一次问清；
它不会一上来把学习变成考试，也不会突然从损失函数、张量形状或注意力开始。

## 它和普通学习对话有什么不同？

| 普通对话容易出现的问题 | Mastery Tutor 的处理 |
|---|---|
| 一上来进入局部技术细节 | 先建立领域地图、终点和前置关系 |
| 把“听懂了”当作“掌握了” | 要求独立回忆、应用和迁移证据 |
| 内容散落在大量聊天消息中 | 持续维护一个清晰、美观的本地 HTML 教室 |
| 答错一次就直接给答案 | 分层提示，并记录完成时用了多少帮助 |
| 新会话忘记之前学了什么 | 在学习工作区的 `.mastery/` 中保存可检查状态 |
| 刚做完一道同类题就宣布学会 | 安排延迟复习；后续失败会把掌握状态降为脆弱 |

这个项目是“研究导向”，不是“效果已经被证明”。自动测试能验证程序和教学契约，不能证明真实学习者
一定学得更快、记得更久。证据与声明边界见
[教学法证据](docs/pedagogy-evidence.md)和[评测说明](docs/evaluation.md)。

## 两个 Skill，一个导师

- **`mastery-coach`**：规划知识图谱、教学、个性化调整、证据判断、复习调度和跨会话恢复。
- **`mastery-tool-creator`**：创建并验证课程页面、代码实验、模拟器、可视化讲解和无障碍备用视图。

唯一源码位于 [`skills/`](skills/)。Codex 等平台包由适配器生成，不能手工维护多份副本。
架构与宿主能力要求见 [docs/architecture.md](docs/architecture.md) 和
[docs/host-contract.md](docs/host-contract.md)。

## 本地数据与安全

学习记录、课件、练习和证据默认保存在你选择的工作区。全局注册表只帮助 AI 找回工作区，不保存完整
学习档案。启用本地代码或浏览器课件前，请阅读 [SECURITY.md](SECURITY.md)。

## 参与项目

开发说明见 [CONTRIBUTING.md](CONTRIBUTING.md)，计划见 [ROADMAP.md](ROADMAP.md)，问题可提交到
[GitHub Issues](https://github.com/fanfanfanfanfan626/mastery-tutor/issues)。

## 许可证

[MIT](LICENSE)
