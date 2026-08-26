# Mastery Learning

**让 AI 教你，但不替你学。**

Mastery Learning 是一个开源的 Codex 学习插件。你告诉它想学什么、现在会什么、每周有
多少时间；它负责安排课程、打开本地 HTML 教室、准备练习和实验，并在下一次对话里接着
上次的进度继续。

[![CI](https://github.com/fanfanfanfanfan626/mastery-learning/actions/workflows/verify.yml/badge.svg)](https://github.com/fanfanfanfan626/mastery-learning/actions/workflows/verify.yml)
[![Latest release](https://img.shields.io/github/v/release/fanfanfanfanfan626/mastery-learning?label=release)](https://github.com/fanfanfanfan626/mastery-learning/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e.svg)](LICENSE)

[让 AI 安装](#让-ai-安装) · [它怎么教](#它怎么教) · [项目文档](#项目文档) · [参与开发](CONTRIBUTING.md) · [English](#english)

![Mastery Learning walkthrough](docs/assets/demo.gif)

## 为什么做这个项目

AI 很会解释知识，却很容易把学习变成连续阅读：它讲得顺，你也觉得听懂了，但换一个题目
就不会做。

Mastery Learning 把过程改成几件更具体的事：先看一个完整例子，再自己动手；提示逐步减少；
换一个情境再做一次；隔一段时间重新回忆。只有观察到这些学习行为，系统才会更新进度。

## 让 AI 安装

把下面这一句话发给 Codex：

```text
请安装这个完整 Codex 插件：https://github.com/fanfanfanfanfan626/mastery-learning 。先读取并严格执行仓库根目录的 AI_INSTALL.md；完成其中全部成功条件前，不要宣称安装成功。
```

这份安装契约会让 AI：

- 把完整仓库放到稳定目录，而不是拆出一个 `SKILL.md`；
- 不使用 `skill-installer`，避免只装上一半；
- 发现旧版独立 Skill 时先告诉你，不会直接删除；
- 只使用电脑上已经可用的 Codex CLI，不会临时下载另一套；
- 安装后通过 `codex plugin list` 再确认一次。

查看完整的 [AI 安装契约](AI_INSTALL.md) 或 [手动安装说明](INSTALL.md)。

> 当前可安装、经过测试的版本是 Codex 插件。教学协议可以适配其他 AI Agent，但尚未验证的
> 平台不会被写成“已支持”。GitHub 分发目前是一条消息交给 AI 安装；插件目录里的 `+` 按钮
> 安装需要项目进入公开插件目录。

安装完成后，新建一个 Codex 任务，像平时说话一样提出目标：

```text
我想从零系统学习机器学习和大模型，最后能训练、理解并改造模型。每天可以投入 30 分钟。
```

## 它怎么教

一次正常学习不会从突然出现的考试开始。

1. **先确定方向**：用一张可跳过的启动卡了解目标、基础、时间和偏好。
2. **建立地图**：先说明这门领域在解决什么问题，再选择当前需要的路径。
3. **完成一节课**：在本地 HTML 教室里看例子、代码注释、图示和当前任务。
4. **自己尝试**：先预测，再操作或写代码；需要时逐层给提示。
5. **换个场景**：用不同数据、约束或问题检查能不能迁移。
6. **以后再问**：把需要巩固的内容放进复习队列，下次对话继续。

机器学习、AI 和大模型路线从领域全景开始，不会把损失函数、梯度、张量形状或注意力题
当作没有上下文的第一课。

## 你会看到什么

- 一个统一的本地 HTML 教室，用来呈现启动、讲解、反馈、复习和总结；
- 代码练习、测试、提示和 rubric，目标实现仍由学习者完成；
- 需要动起来才能看懂的交互实验，例如注意力、优化和概率模拟；
- 当前学习路径、到期复习和已经观察到的能力；
- 可以检查、导出和删除的 `.mastery/` 本地记录。

简单解释不会为了“好看”额外生成复杂工具。动态概念需要实验时，配套的
`mastery-tool-creator` 会创建并验证可复用课件。

## 和普通 AI 对话有什么不同

| 普通对话常见情况 | Mastery Learning 的处理 |
|---|---|
| 一口气讲很多内容 | 每次保留一个当前任务，其余内容放进路径 |
| 用户说“懂了”就继续 | 只记录实际做过的解释、练习、迁移和复习 |
| 提示后做对也算掌握 | 区分独立完成与辅助完成 |
| 新对话重新开始 | 从本地工作区恢复进度 |
| AI 直接写完目标代码 | AI 准备环境和反馈，学习者保留实现权 |
| 课程表越长越显得完整 | 完整知识图谱留在后台，眼前只显示下一步 |

## 适合与不适合

适合想长期学习编程、数学、机器学习、人工智能或大模型，并愿意实际做题、写代码或完成
项目的人。内置的 ML/AI/LLM 课程图包含 49 个相互连接的能力节点，也可以换成其他主题。

如果你只想得到一个事实答案、快速生成一段成品代码，或者完全不想练习，这个插件不会比
普通聊天更省事。

## 两个 bundled Skills

- **`mastery-coach`**：负责目标、课程、课堂、练习、反馈、复习和学习记录。
- **`mastery-tool-creator`**：负责生成代码实验、可视化课件和其他需要验证的教学工具。

它们作为一个 `mastery-learning` 插件安装。不要使用 `skill-installer` 分开复制。

## 数据放在哪里

学习内容保存在你选择的工作区 `.mastery/` 目录里。跨任务注册表只保存工作区路径、目标和
更新时间。默认没有云数据库、账号、API Key 或遥测。

记录可以验证、重建、迁移、导出和删除。生成的工具也会绑定文件哈希；内容修改后，原来的
验证状态会失效。

## 项目文档

- [安装与故障边界](INSTALL.md)
- [产品规则](docs/product-spec.md)
- [架构](docs/architecture.md)
- [教学法证据与限制](docs/pedagogy-evidence.md)
- [评测计划](docs/evaluation.md)
- [扩展课程和工具](docs/authoring.md)
- [路线图](ROADMAP.md)

## 验证

```bash
python plugins/mastery-learning/skills/mastery-coach/scripts/curriculum_audit.py
python quality/eval_audit.py suite quality/evals/plugin-evals.json
python -m unittest discover -s quality -p "test_*.py" -v
```

CI 在 Windows 和 Linux 上运行测试、课程审计、安装契约检查和可复现发布包检查。程序测试
证明规则按预期执行，不证明真实学习者一定学得更快；项目对这两种证据分开表述。

## 参与开发

如果你用过项目，最有帮助的反馈是一个具体时刻：哪一步不清楚、哪节课太累、哪个提示给得
太早，或者哪次恢复进度失败。可以直接提交 [Issue](https://github.com/fanfanfanfan626/mastery-learning/issues)，
也可以从 [`good first issue`](https://github.com/fanfanfanfan626/mastery-learning/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
开始。

## English

Mastery Learning is an open-source Codex plugin for people who want to learn by doing. Tell it what
you want to learn and how much time you have. It plans a route, opens a local HTML classroom,
prepares exercises and interactive labs, checks independent work and later recall, and resumes from
local progress in a new task. The current packaged implementation supports Codex; other agent
adapters are not claimed until they are tested.

## License

MIT
