# Mastery Tutor

**面向 AI Agent 的本地优先掌握式学习导师。**

它把引导式 HTML 课程、动手练习、迁移检验、间隔复习和可检查的学习进度放在同一套工作流里。
学习记录保存在你选择的本地工作区，而不是某个远程账号中。

它是一个由两个 Skill 协作的完整产品：`mastery-coach` 负责教学和学习记录，
`mastery-tool-creator` 只在课程确实需要时创建交互实验。

[产品网页](https://fanfanfanfanfan626.github.io/mastery-tutor/) · [English](README.md) · [AI 一句话安装](AI_INSTALL.md) · [手动安装](INSTALL.md) ·
[兼容状态](COMPATIBILITY.md)

> **发布状态：** `main` 是下一版候选代码。当前公开安装包仍使用旧的 Mastery Learning 身份；
> 在 E2 证据门禁与标签发布流程通过前，不把 `main` 描述成已经正式发布的完整适配器。

![Mastery Tutor 真实反馈课堂](docs/assets/classroom-feedback-real.png)

*这是确定性课堂渲染器的真实输出：重试页保留原题、学习者回答、最早错误与第 1 级提示，并且不泄露答案。
仓库同时保存了[输入与逐字节截图溯源](docs/assets/classroom-feedback-real.provenance.json)。*

<details><summary>查看端到端流程示意动画</summary>

![Mastery Tutor 流程示意](docs/assets/demo.gif)

第二张图是产品流程示意，不是真实学习者会话录屏。
</details>

| AI 宿主 | 当前状态 | 分发形式 |
|---|---|---|
| Codex | **工程已验证 · 对话证据待完成** | 完整插件 |
| Claude Code | 实验性 | 两个 Skill |
| GitHub Copilot | 实验性 | 两个 Skill |
| 通用 Agent Skills 宿主 | 核心兼容 | 两个 Skill |
| OpenCode | 计划中 | 尚未发布 |

“工程已验证”表示安装包和确定性引擎通过 E0/E1 检查，不代表全新 AI 对话已经通过 E2。
“核心兼容”只表示宿主能够发现并安装两个标准 Skill。每个状态的证据见 [COMPATIBILITY.md](COMPATIBILITY.md)。

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

第一次使用会打开一张紧凑、可跳过的入门教室卡片，把目标、背景、时间和教学偏好一次问清。
第一课先让学习者看到、预测并操作一个具体问题，再给这个想法命名；不会一上来考试或堆术语。

## 它和普通学习对话有什么不同？

| 普通对话容易出现的问题 | Mastery Tutor 的处理 |
|---|---|
| 一上来讲定义或领域分类 | 从具体问题、预测、揭示结果和一次引导应用开始 |
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

支持子 Agent 的宿主可以在复杂课程背后按需启用规划、学科审查、网页设计和独立验收；学习者始终只面对
一个主教师，也只有一个组件可以写入学习状态。单 Agent 宿主仍遵守同一套教学契约。

唯一源码位于 [`skills/`](skills/)。Codex 等平台包由适配器生成，不能手工维护多份副本。

## 内置课程范围

教学引擎可以根据学习者提供的教材、论文、代码仓库和自定义知识图工作。目前唯一内置并经过来源审计的
课程包是机器学习、人工智能与大语言模型。课程包以外的编程或数学需要显式建立自定义知识图；项目不宣称
已经为所有学科提供完整的现成教纲。
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

## 相关项目

- [Idea Council](https://github.com/fanfanfanfanfan626/challenge-and-refine-ideas)：在实施前澄清并反证想法。
- [Persistent AI Studio](https://github.com/fanfanfanfanfan626/orchestrate-agent-organization)：治理跨任务、已经获得授权的多 Agent 产品工作。
