# study-flow

一个面向 Claude Code / Codex 的技能（skill）：把课程课件、教材、笔记和作业，整理成**可追溯、可续写、适合期末复习**的离线 HTML 学习库。

理工、计算机、经管、医学、人文社科及语言类课程通用。默认中文交流；遇到英文材料自动切换到完整的双语解题流程。

## 它做什么

- **知识点整理**：从课件/教材/笔记中提取核心概念、公式理论及适用条件、推导论证、全部涉及题型、例题与易错点，按固定章节架构落盘。
- **作业解题**：支持图片、扫描页与文档作业。按材料语言分流，不强行统一。
- **公式忠实渲染**：所有公式用本地 KaTeX 真正排版，保留原式的符号、上下标、分式、向量、矩阵、多行结构与编号；不支持或看不清时用原公式裁图保底，不用代码框、ASCII 近似或裸 LaTeX 代替。
- **期末复习资产**：默认生成 HTML 总目录、章节总结页、作业解析页，带侧栏导航、离线关键词搜索、作业原图直达与原位返回、可打印（含自测答案展开）。
- **增量续写**：已有学习库时按 SHA-256 内容指纹识别新增/变化/未完成材料，只处理增量，不重做旧内容、不生成重复页。

## 语言分流规则

| 材料 | 分支 | 输出 |
| --- | --- | --- |
| 中文为主要叙述，夹有少量英文术语/标题/缩写 | 中文 | 原题 → 中文解题过程与解析 → 公式定理/理论依据 → 易错点 |
| 主要题干或教学叙述为英文 | 英文 | 原题 → 中文翻译 → 中英术语对照 → English Solution → 中文解析 → 公式/理论依据 → 易错点 |
| 不同页/题语言不同 | 逐页/逐题分流 | 同一学习库允许两种分支共存 |

注意：出现 GDP、DNA、Python、向量 i/j 等**不**构成英文材料；中文题干要求"用英语写一封信"时仍完成英文信件，但不附加整套双语包装。

## 目录结构

```text
study-flow/
├── SKILL.md                        # 技能主入口：工作流与行为约束
├── agents/openai.yaml              # Codex 侧界面描述
├── references/
│   ├── content-flow.md             # 内容整理与解题规范、学科适配与验证
│   ├── html-design.md              # 固定 HTML 架构、UI、搜索、原图交互规范
│   ├── formula-rendering.md        # 原式忠实渲染与核验标准
│   └── library-flow.md             # 学习库结构、增量更新与索引
├── scripts/
│   ├── build_page.py               # 从 JSON 规格生成固定模板 HTML
│   ├── build_search_index.py       # 从实际 HTML 重建离线搜索索引
│   ├── check_library.py            # 校验本地链接、锚点与资源（只读）
│   └── scan_updates.py             # 识别新增/变化材料，登记已处理范围
└── assets/
    ├── study-ui.css / study-ui.js  # 唯一基础视觉样式与本地渲染/交互运行时
    ├── examples/                   # 三种架构的内容规格样例 + 演示原图
    └── vendor/katex/               # 固定版本 KaTeX 0.16.22 + mhchem + 字体 + 许可证
```

生成的课程资产放在用户的课程目录（默认 `study-library/<课程简称>/`），**不放在技能安装目录**，也不写入全局记忆。

## 安装

克隆到 Claude Code 或 Codex 的技能目录：

```bash
# Claude Code
git clone git@github.com:white-sand-grand/study-flow-skills.git ~/.claude/skills/study-flow

# Codex
git clone git@github.com:white-sand-grand/study-flow-skills.git ~/.codex/skills/study-flow
```

无第三方 Python 依赖，脚本只用标准库。

## 使用

在对话中声明使用即可，例如：

```text
使用 study-flow 整理这些课件
使用 study-flow 解一下这份作业（附图片）
用 study-flow 做期末复习整合
```

技能会先识别材料语言并说明选用的分支与将要更新的学习库，再开始整理。

## 脚本用法

```bash
python <技能目录>/scripts/build_page.py <内容.json> --library <课程库目录> --page <页面.html>
python <技能目录>/scripts/build_search_index.py <课程库目录>
python <技能目录>/scripts/check_library.py <课程库目录>

python <技能目录>/scripts/scan_updates.py scan --course <课程目录> --library <课程库目录>
python <技能目录>/scripts/scan_updates.py record --course <课程目录> --library <课程库目录> \
    --source <已处理文件> --scope <章节/题号范围> --sha256 <处理前指纹> --page <页面.html> --status complete
```

- 页面规格字段见 `assets/examples/*.json`；默认拒绝覆写已有页，确需更新用 `--replace`。
- `check_library.py` 只校验本地引用是否可解析，不证明内容正确或渲染正确。

## 交付前的验证要求

技能内置硬性验收项，未通过不得声称完成：

1. **内容**：选题与子问覆盖齐全、源文/译文一致、两种语言结果一致、依学科做代回/量纲/极限/样例运行等核验。
2. **结构**：`check_library.py` 无 `FAIL`。
3. **公式**：所有 `[data-tex]` 节点渲染成功（`data-math-state="rendered"`），且逐式对照原材料——渲染成功不等于转录正确。
4. **视觉**：桌面（约 1440px）、390px 手机宽度与打印布局实际检查；断网复检公式与字体可用。
5. 工具不可用时照样产出资产，但明确列出未核验项，不伪称通过。

## 设计约束（为什么看起来"固定"）

- 深蓝 `#142b4b` 页头、灰白背景、靛蓝 `#355bc2` 链接，蓝色提示 / 绿色答案 / 琥珀警示三类语义框。
- 桌面左侧目录 + 右侧正文，850px 以下单列；侧栏可关闭并通过固定入口重新打开。
- 禁止用 `overflow-x:hidden` 隐藏内容；长表格与宽公式只在自己容器内横向滚动。
- 答案默认可见，只折叠自测答案；打印前自动展开答案、隐藏导航、白底深字。
- 不引入 CDN、不引入外部搜索，`file://` 直接打开即可完整使用。

## License

技能本身按仓库默认许可分发。`assets/vendor/katex/` 为 KaTeX，MIT License，Copyright (c) 2013-2020 Khan Academy and other contributors，许可证随包提供。
