# Mastery Learning for Codex

> [!IMPORTANT]
> **安装类型：Codex 插件市场（Codex plugin marketplace），不是根目录独立 Skill。不要使用 `skill-installer`。**
> 本仓库把 `mastery-coach` 与 `mastery-tool-creator` 作为一个插件共同安装；只复制其中一个
> `SKILL.md` 会得到不完整且不受支持的安装。完整说明见 [INSTALL.md](INSTALL.md)。

Mastery Learning 是一个以 Codex 为核心交互界面的开源学习系统。它不是独立学习网站：用户在 Codex 中说出目标，Codex 负责诊断、规划、教学、出题、检查代码、生成实验工具、记录证据并安排复习。

产品核心是 `mastery-coach` Skill。GitHub 插件只是安装、发现和版本管理外壳；`mastery-tool-creator` 是被主 Skill 显式调用的教学工具工厂。

## 它解决什么

普通 AI 教学容易把“解释得顺”误当成“学生学会了”。本系统要求：

- 开始时用一张可跳过的简短启动卡了解相关背景、熟悉度和教学偏好，不先用考试拦住学习；
- 同时维护完整覆盖图和当前学习路径；
- 完整课程图始终保留；用户确认的目标画像和显式目标决定必修先修闭包，未选择内容不会污染完成率；
- 每次教学都经过预测、尝试、反馈、迁移和记录；
- 代码学习由学习者完成目标代码，Codex 提供脚手架、测试和递进提示；
- 只有每个要求维度都有独立证据，并同时通过延迟检索和迁移任务，才标记为掌握；
- 学习记忆保存在本地 `.mastery/`，用户可读、可迁移、可导出、可删除；概念要求不能被单条证据缩减；
- 可视化、3D、黑板、Notebook、PPT 和测验按需生成，不是固定 UI。

## 安装（推荐：让 Codex 完成）

最简单只需把下面一句交给 Codex；详细路由和校验规则由仓库自己提供，不需要用户背安装步骤：

```text
请把这个仓库作为 Codex 插件（不是独立 Skill）安装：https://github.com/fanfanfanfanfan626/mastery-learning 。按根目录 INSTALL.md 完成并验证。
```

手动安装也只需在完整 Git clone 或完整 Release ZIP 的根目录运行一条命令：Windows 使用
`powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1`，macOS/Linux 使用
`sh ./install.sh`。脚本会先验证 marketplace 与 plugin 两层身份，再通过 Codex CLI 安装；不会回退成单 Skill 安装。下载、校验、稳定目录要求和故障处理见 [INSTALL.md](INSTALL.md)。

安装或更新后开启一个新的 Codex 任务，使两个 Skill 被重新加载。不要把 GitHub 密码或令牌粘贴进对话；如需推送仓库，请使用 Codex 内置浏览器或 GitHub CLI 的官方登录流程。

## 开始使用

可以直接对 Codex 说：

```text
我想系统学习机器学习、AI 和大模型，目标是能独立构建并评估可靠的 LLM 应用。每周 6 小时。请用一张简短启动卡一次了解我的基础和教学偏好，然后直接开始引导学习，不要先考试或给我完整课程。
```

继续学习：

```text
读取我的本地学习进度，先处理到期复习，再决定今天学什么。
```

主 Skill 会先从持久工作区注册表中定位过去的学习目录；注册表采用每工作区一个原子条目，存在多个目标时会让用户选择。首次学习会把目标、时间、相关背景、6–8 个“会用/听过/没学过/跳过”的能力定位、教学体验和本地保存放进同一张可跳过的启动卡。用户一次回复后才初始化完整课程图；自述只作为待验证假设，不写成学习证据，并在同一回复里开始第一个引导式微课。目标画像和先修闭包只有经用户明确选择才写入必修范围。不会把生成型 Codex 任务目录误当作永久学习空间。旧 schema v1/v2/v3 会先生成外部 ZIP，再保守迁移到 v4。

创建工具：

```text
这部分仅靠文字不好理解。请让工具生成器制作一个需要我先预测、再操作、最后解释迁移的可视化实验。
```

新目标和新概念默认使用引导模式：先给一个具体模型或样例、共同完成一步，再逐渐减少帮助；已有可用基础后才进入强调独立尝试的教练模式。启动时只需选择一个可随时修改的体验预设（引导、项目、严谨或挑战），也可覆盖语气、课外作业和正式检查偏好。费曼式讲回、样例渐隐、交错练习、对比案例、生产性失败等方法由 AI 按当前知识和错误选择，不要求用户配置，也不会改变掌握标准。

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

更多说明见 [架构](docs/architecture.md)、[产品规则](docs/product-spec.md)、[教学法证据与声明边界](docs/pedagogy-evidence.md)、[评测与学习效果计划](docs/evaluation.md) 和 [扩展指南](docs/authoring.md)。

## 验证

```bash
python plugins/mastery-learning/skills/mastery-coach/scripts/curriculum_audit.py
python quality/eval_audit.py suite quality/evals/plugin-evals.json
python -m unittest discover -s quality -p "test_*.py"
python quality/build_release.py --output work/mastery-learning.zip --checksum-output work/mastery-learning.zip.sha256
python quality/release_audit.py archive work/mastery-learning.zip --expected-version 0.4.2
```

发布前还应使用 Codex 自带的 `skill-creator/quick_validate.py` 和 `plugin-creator/validate_plugin.py` 校验，构建后从 ZIP 解压目录复跑，并从全新 Codex 任务完成对话评测。CI 在 Windows 和 Linux 上执行故障与反例测试，分别构建发布包、对照 Git 树审计，并比较两个平台的 ZIP 是否字节一致。标签构建会生成 GitHub provenance attestation。

自动化程序测试证明工程约束被实现，不证明真实学习效果。只有在提交与场景哈希绑定的完整评测结果后，才能声明对应的 Codex 对话行为已经验证；“提高学习效果”还需要真实学习者的延迟检索和迁移结果。参见 [评测分级](docs/evaluation.md) 与 [教学法证据边界](docs/pedagogy-evidence.md)。

`v0.4.2` 标签发布门禁要求三次具有唯一运行 ID、时间戳和转录指纹的完整、可审查合成对话评测；结果目录是封闭集合，改名或未引用的旁路文件会被拒绝。不得有 `blocked/not-run`，关键安全与教学边界案例每次都必须通过，全部案例的总体通过率至少为 90%，每个普通案例至少通过三次中的两次。失败记录仍须如实保留；它们不能再仅凭“记录完整”满足发布门禁。本地验证器无法观察从未记录到结果根目录的外部运行，因此正式审查仍需核对任务来源和 Git 历史。

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
