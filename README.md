# Mastery Learning for Codex

Mastery Learning 是一个以 Codex 为核心交互界面的开源学习系统。它不是独立学习网站：用户在 Codex 中说出目标，Codex 负责诊断、规划、教学、出题、检查代码、生成实验工具、记录证据并安排复习。

产品核心是 `mastery-coach` Skill。GitHub 插件只是安装、发现和版本管理外壳；`mastery-tool-creator` 是被主 Skill 显式调用的教学工具工厂。

## 它解决什么

普通 AI 教学容易把“解释得顺”误当成“学生学会了”。本系统要求：

- 先用任务诊断，而不是只问“你会多少”；
- 同时维护完整覆盖图和当前学习路径；
- 完整课程图始终保留；用户确认的目标画像和显式目标决定必修先修闭包，未选择内容不会污染完成率；
- 每次教学都经过预测、尝试、反馈、迁移和记录；
- 代码学习由学习者完成目标代码，Codex 提供脚手架、测试和递进提示；
- 只有每个要求维度都有独立证据，并同时通过延迟检索和迁移任务，才标记为掌握；
- 学习记忆保存在本地 `.mastery/`，用户可读、可迁移、可导出、可删除；概念要求不能被单条证据缩减；
- 可视化、3D、黑板、Notebook、PPT 和测验按需生成，不是固定 UI。

## 从 GitHub 安装

克隆仓库，再把包含 `.agents/plugins/marketplace.json` 的仓库根目录注册为显式本地插件目录：

```powershell
git clone https://github.com/fanfanfanfanfan626/mastery-learning.git
Set-Location .\mastery-learning
codex plugin marketplace add (Resolve-Path .)
codex plugin add mastery-learning@mastery-learning
```

macOS/Linux 把第三条改为 `codex plugin marketplace add "$(pwd)"`。

## 从发布 ZIP 安装

不需要 GitHub 地址。下载 `mastery-learning-0.4.1.zip`，完整解压后，把解压根目录注册为显式本地插件目录：

```powershell
Expand-Archive .\mastery-learning-0.4.1.zip -DestinationPath .\mastery-learning-0.4.1
codex plugin marketplace add (Resolve-Path .\mastery-learning-0.4.1)
codex plugin add mastery-learning@mastery-learning
```

macOS/Linux 可改用 `unzip mastery-learning-0.4.1.zip -d mastery-learning-0.4.1`，其余两条命令相同，并传入解压根目录的绝对路径。不要把 ZIP 内的 `plugins/mastery-learning` 子目录误当成 marketplace 根目录；需要注册的是同时包含 `.agents/`、`plugins/` 的那一层。

安装或更新后开启一个新的 Codex 任务，使 Skill 被重新加载；在桌面版中也可从 Plugins Directory 安装已添加目录中的 `mastery-learning`。不要把 GitHub 密码或令牌粘贴进对话；如需推送仓库，请使用 Codex 内置浏览器或 GitHub CLI 的官方登录流程。

## 开始使用

可以直接对 Codex 说：

```text
我想系统学习机器学习、AI 和大模型，目标是能独立构建并评估可靠的 LLM 应用。每周 6 小时，请先诊断，不要直接给我完整课程。
```

继续学习：

```text
读取我的本地学习进度，先处理到期复习，再决定今天学什么。
```

主 Skill 会先从持久工作区注册表中定位过去的学习目录；注册表采用每工作区一个原子条目，存在多个目标时会让用户选择。首次学习会先与用户确定稳定目录、解释本地数据，再初始化完整课程图并记录诊断；提出目标画像和先修闭包后，只有经用户确认才写入必修范围。不会把生成型 Codex 任务目录误当作永久学习空间。旧 schema v1/v2/v3 会先生成外部 ZIP，再保守迁移到 v4。

创建工具：

```text
这部分仅靠文字不好理解。请让工具生成器制作一个需要我先预测、再操作、最后解释迁移的可视化实验。
```

主 Skill 默认使用教练模式，一次提出一个有意义的学习动作。可以明确切换演示、结对、考试或复习模式。

## 仓库结构

```text
.agents/plugins/marketplace.json        # GitHub/团队插件目录
plugins/mastery-learning/
├── .codex-plugin/plugin.json           # Codex 插件元数据
└── skills/
    ├── mastery-coach/                   # 核心教学 Skill
    │   ├── SKILL.md
    │   ├── references/                  # 教学、评估、个性化、来源与教纲规则
    │   ├── assets/curricula/            # 机器可审计教纲包
    │   └── scripts/mastery.py           # 本地学习状态与复习引擎
    └── mastery-tool-creator/            # 显式调用的工具工厂
        ├── SKILL.md
        ├── assets/                      # 工具 manifest schema
        └── scripts/                     # 脚手架、静态校验与外部观察归档
```

更多说明见 [架构](docs/architecture.md)、[产品规则](docs/product-spec.md) 和 [扩展指南](docs/authoring.md)。

## 验证

```bash
python plugins/mastery-learning/skills/mastery-coach/scripts/curriculum_audit.py
python -m unittest discover -s quality -p "test_*.py"
```

发布前还应使用 Codex 自带的 `skill-creator/quick_validate.py` 和 `plugin-creator/validate_plugin.py` 校验，构建后从 ZIP 解压目录复跑，并从一个全新 Codex 任务完成冷启动与恢复验收。CI 在 Windows 和 Linux 上执行不依赖 Codex 安装环境的故障与反例测试。

## 隐私与安全

- 默认不需要云数据库、独立账号、API Key 或遥测。
- `.mastery/` 可能包含目标、错误和学习表现；每个学习空间都会生成保护性的 `.mastery/.gitignore`。公开仓库前仍需再次检查。
- 跨任务注册表只保存学习目录路径、目标和更新时间；可以通过状态引擎导出完整 ZIP，删除需要精确目录和显式确认词。
- 状态写入使用操作系统锁、可恢复事务日志和提交版本；中断后的下一条命令会先恢复完整版本。损坏的证据或会话行不会被静默跳过。
- 工具静态校验器绝不执行生成代码；它按语言拒绝网络、进程和动态代码能力，要求 HTML 资源形成工具目录内的闭包，并对每个 HTML 页面强制本地运行 CSP。Codex 仍需在独立沙箱调用中运行检查/渲染，再归档观察结果。验证报告绑定当前文件哈希，编辑后必须重新验证，否则状态为 `stale`。命令白名单和静态分析都不被宣称为操作系统沙箱。
- Skill 可以提出自我改进建议，但不会静默修改自身规则或教纲。

## 开源参考

设计吸收了 [SkillCoco](https://github.com/skillcoco/skillcoco) 的可审计掌握循环、[OpenTutor](https://github.com/zijinz456/OpenTutor) 的本地学习状态、[Learn FASTER](https://github.com/hluaguo/learn-faster-kit) 的编码代理教学、[FSRS4Anki](https://github.com/open-spaced-repetition/fsrs4anki) 的数据驱动复习思想，以及 [JupyterLite](https://github.com/jupyterlite/jupyterlite) 的零安装实验方向。当前实现不复制这些项目的代码。

## License

MIT
