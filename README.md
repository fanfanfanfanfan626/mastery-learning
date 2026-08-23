# Mastery Learning for Codex

**Turn Codex into a local-first AI tutor that teaches, checks understanding, builds interactive labs, and remembers real progress.**

把 Codex 从“会解释问题的聊天助手”变成一套可持续使用的 AI 学习教练：目标规划、引导教学、代码练习、可视化实验、掌握证据与间隔复习都在同一条对话里完成。

[![CI](https://github.com/fanfanfanfanfan626/mastery-learning/actions/workflows/verify.yml/badge.svg)](https://github.com/fanfanfanfanfan626/mastery-learning/actions/workflows/verify.yml)
[![Latest release](https://img.shields.io/github/v/release/fanfanfanfanfan626/mastery-learning?label=release)](https://github.com/fanfanfanfanfan626/mastery-learning/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e.svg)](LICENSE)
[![Local-first](https://img.shields.io/badge/data-local--first-7c3aed.svg)](#隐私与安全)

[快速安装](#60-秒开始使用) · [为什么不同](#为什么不是普通-ai-导师) · [路线图](ROADMAP.md) · [参与贡献](CONTRIBUTING.md) · [English summary](#english-summary)

![Mastery Learning for Codex demo: goal, guided lesson, interactive lab, mastery evidence, and review](docs/assets/demo.gif)

> AI 很容易让人产生“听懂了就是学会了”的错觉。Mastery Learning 把掌握建立在独立练习、迁移和延迟检索证据上，而不是建立在自信或一次顺利回答上。

> [!IMPORTANT]
> 这是一个完整的 **Codex plugin marketplace**，不是根目录独立 Skill。请安装整个仓库，不要使用 `skill-installer`，也不要只复制某个 `SKILL.md`。完整安装边界见 [INSTALL.md](INSTALL.md)。

## 30 秒看懂

| 你做什么 | Codex 做什么 | 得到什么 |
|---|---|---|
| 说出“我想学大模型，每天 30 分钟” | 一次性了解目标、基础和偏好 | 可调整的学习边界，而不是一张巨大课表 |
| 开始一个新概念 | 先示范，再让你预测、操作和解释 | 一节适合当前基础的引导式微课 |
| 文字不够直观 | 生成并验证本地 HTML、代码或可视化实验 | 可以动手探索的教学工具 |
| 完成练习 | 区分独立完成、提示完成与失败 | 不会虚构的掌握记录 |
| 下次继续 | 恢复本地进度并安排到期复习 | 跨 Codex 任务持续学习 |

## 60 秒开始使用

把下面一句交给 Codex：

```text
请把这个仓库作为完整 Codex 插件安装：https://github.com/fanfanfanfanfan626/mastery-learning 。读取根目录 AGENTS.md 和 INSTALL.md，完成安装并验证；不要使用 skill-installer。
```

安装后新建一个 Codex 任务，直接说：

```text
我想系统学习机器学习、AI 和大模型，目标是能训练、理解并改造模型。每天 20–40 分钟。请先用一张简短、可跳过的启动卡一次了解我的基础和教学偏好，然后直接开始引导学习，不要先考试。
```

<details>
<summary>手动安装</summary>

从完整 Git clone 或 Release ZIP 的根目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

```bash
sh ./install.sh
```

脚本会验证 marketplace 与 plugin 两层身份，再通过 Codex CLI 安装；不会降级成不完整的单 Skill 安装。详见 [INSTALL.md](INSTALL.md)。
</details>

## 为什么不是普通 AI 导师

| 常见 AI 教学 | Mastery Learning |
|---|---|
| 连续解释，默认用户跟上了 | 从已知模型开始，逐步减少帮助 |
| 一上来考试或连续追问设置 | 一张可跳过的启动卡，一次回复后开课 |
| 用户说“懂了”就继续 | 独立证据、迁移和延迟检索共同决定掌握 |
| 每次对话重新开始 | 本地 `.mastery/` 状态可恢复、导出和删除 |
| 代码答案由 AI 直接写完 | 学习者保留目标代码所有权，Codex 提供测试和递进提示 |
| 可视化只是装饰 | 工具必须支持预测、操作、解释、迁移和可访问回退 |

本项目采用检索练习、间隔学习、样例渐隐、费曼式讲回、对比案例和掌握学习等研究导向方法，但不会把工程测试宣传成真实学习效果证明。依据与限制见 [教学法证据地图](docs/pedagogy-evidence.md) 和 [评测计划](docs/evaluation.md)。

## 适合谁

- 想系统学习 Python、数学、机器学习、AI 或大模型，而不是只收集回答的人；
- 希望 Codex 能记住学习进度，但不愿把学习画像交给云数据库的人；
- 需要代码实验、交互式 HTML 微课、Notebook、测验或项目反馈的自学者；
- 想研究 AI tutor、mastery learning、spaced repetition 或可审计 Agent 工作流的开发者。

## 核心能力

- **目标与路径**：同时保留完整知识图谱和学习者确认的当前路径，未选择内容不污染完成率。
- **从零教学**：重要概念可生成约 20–40 分钟的 `lesson_lab`，包含完整例题、教学注释、同步可视化、练习和迁移。
- **代码学习**：Codex 创建脚手架、测试、rubric 和分层提示，目标实现留给学习者。
- **可靠掌握**：提示完成、同会话重复和自信陈述不能伪造掌握；掌握后失败会降为 `fragile`。
- **复习调度**：按到期证据安排检索，区分必修、拓展和范围外项目。
- **本地记忆**：状态可验证、重建、迁移、导出和删除；跨任务注册表只记录路径与目标。
- **受控工具生成**：HTML、代码、可视化和文档工具经过静态检查、真实观察、哈希绑定与失效处理。

继续学习时只需说：

```text
读取我的本地学习进度，先处理到期复习，再决定今天学什么。
```

需要可视化时可以说：

```text
这部分仅靠文字不好理解。请制作一个需要我先预测、再操作、最后解释迁移的可视化实验。
```

## 仓库结构

```text
.agents/plugins/marketplace.json        # Codex 插件目录
plugins/mastery-learning/
├── .codex-plugin/plugin.json           # 插件发现与展示元数据
└── skills/
    ├── mastery-coach/                   # 核心 AI 教学 Skill
    │   ├── references/                  # 教学、评估、个性化和来源规则
    │   ├── assets/curricula/            # 可审计教纲包
    │   └── scripts/mastery.py           # 本地状态与复习引擎
    └── mastery-tool-creator/            # 受控教学工具工厂
        ├── assets/                      # manifests 与 lesson_lab 模板
        └── scripts/                     # 脚手架、校验和观察归档
```

更多说明：[架构](docs/architecture.md) · [产品规则](docs/product-spec.md) · [教学法证据](docs/pedagogy-evidence.md) · [评测计划](docs/evaluation.md) · [扩展指南](docs/authoring.md)

## 验证

```bash
python plugins/mastery-learning/skills/mastery-coach/scripts/curriculum_audit.py
python quality/eval_audit.py suite quality/evals/plugin-evals.json
python -m unittest discover -s quality -p "test_*.py" -v
python quality/build_release.py --output work/mastery-learning.zip --checksum-output work/mastery-learning.zip.sha256
python quality/release_audit.py archive work/mastery-learning.zip --expected-version 0.4.2
```

CI 在 Windows 和 Linux 上运行测试、课程审计、发布包审计及跨平台字节一致性检查。自动化测试证明工程约束被实现，不证明用户学得更快或记得更久；真实效果需要独立的学习者试用和延迟结果。

## 隐私与安全

- 默认不需要云数据库、独立账号、API Key 或遥测。
- `.mastery/` 可能包含目标、错误和学习表现，默认由工作区 `.gitignore` 保护。
- 注册表只保存学习目录路径、目标和更新时间。
- 状态写入使用操作系统锁、可恢复事务和一致性验证。
- 生成工具的静态校验器不执行代码；外部观察与文件哈希决定工具是否仍然可信。

## 参与项目

当前优先级是降低首次安装和首次学习摩擦，并收集真实用户反馈，而不是继续堆叠功能。参见 [ROADMAP.md](ROADMAP.md) 和 [CONTRIBUTING.md](CONTRIBUTING.md)，也欢迎从标记为 [`good first issue`](https://github.com/fanfanfanfanfan626/mastery-learning/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) 的任务开始。

如果你试用了项目，最有价值的反馈不是“好不好”，而是：**哪一步让你最想放弃？**

## English summary

Mastery Learning is an open-source, local-first AI tutor plugin for Codex. It turns a learning goal into adaptive lessons, interactive labs, coding practice, evidence-based mastery checks, and spaced review. It is especially suited to programming, mathematics, machine learning, artificial intelligence, and large language models. Learner state stays on the local machine, and the project makes no claim that passing engineering tests proves improved learning outcomes.

## License

MIT
