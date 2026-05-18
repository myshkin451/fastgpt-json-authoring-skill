# FastGPT JSON Authoring Skill

> 面向生产环境的 FastGPT / AIBuilder 工作流 JSON 生成、检查与修复技能。
> Production-grade FastGPT / AIBuilder workflow JSON authoring, inspection, and repair.

关键词 / Keywords:
`FastGPT`, `AIBuilder`, `Sangfor AIBuilder`, `FastGPT JSON`, `workflow JSON`,
`JSON generator`, `AI agent skill`, `RAG workflow`, `LLMOps`, `canvas workflow`.

## 中文简介

FastGPT 画布很适合快速搭应用，但当工作流进入真实业务场景后，它本质上就不再只是“拖节点”：

- `chatConfig.variables` 是应用状态；
- `nodes` 是一组有运行时契约的算子；
- `edges` 是执行路径；
- HTTP、知识库、表单、判断器、AI 节点之间靠引用和输出 ID 协同；
- 导出 JSON 一旦字段形状、handle、output id、知识库绑定不对，就可能出现“能导入但打不开画布”或“能打开但预览跑不通”。

这个项目的目标是把 FastGPT 导出 JSON 当作**可审查、可测试、可修复、可重复生成的工程产物**，而不是一次性手工画布配置。

它不是只面向某一个 Agent 平台的小工具，而是一个平台中立的 skill 包：适合任何支持 skill / prompt-pack / agent workflow 的 AI 编程助手使用。

说明：这是一个独立工程化 skill 项目，适用于 FastGPT / AIBuilder /
Sangfor AIBuilder 风格的导出 JSON 开发与校验；不代表任何厂商官方立场。

## 核心定位

**一句话：用真实导出样本校准，生成可导入、可检查、可演进的工业级 FastGPT 应用 JSON。**

本项目特别强调：

- **同版本导出优先**：优先复制目标 FastGPT 环境真实导出的节点形状，而不是只相信抽象 schema。
- **画布即图程序**：先设计节点、边、变量、输出引用，再生成 JSON。
- **确定性检查**：用脚本检查节点、边、handle、变量、HTTP、知识库、catch 分支、secret 泄漏。
- **生产交付口径**：区分 `static-validated`、`import-validated`、`runtime-validated`，不把“JSON 能 parse”吹成“生产可用”。
- **业务安全边界**：权限、客户 ACL、身份、业务状态以后端/API/内部变量为准，不让 LLM 自己判断。

## 和普通模板生成器有什么不同

很多 FastGPT JSON 生成器采用 template-first 思路：从默认模板和通用规则出发，把自然语言需求转成 JSON。这对 demo 很快，也很有价值。

但真实 FastGPT / AIBuilder 环境里，导出格式经常有版本差异：

- HTTP 动态输出有生成的 output id，不能只看 `success` 这个可见 key；
- `formInput` 可能存在字段级输出；
- `{{$VARIABLE_NODE_ID.xxx$}}` 是全局变量插值，不是普通节点引用；
- HTTP body 里的 `{{scenario_key}}` 可能是 HTTP 本地参数，不是旧式全局变量；
- 知识库 dataset id、模型 id、token、API base URL 往往是环境绑定；
- 底部功能入口不一定适合作为暂停节点后的稳定路由。

所以这个项目采用更保守、更适合生产的路线：

```text
目标 FastGPT 环境导出样本
-> 克隆同版本节点形状
-> 编译业务工作流图
-> 静态检查 JSON
-> 导入 FastGPT 副本
-> 预览验证关键路径
```

详细对照见：

- `skills/fastgpt-json-authoring/references/template-first-vs-export-calibrated.md`
- `skills/fastgpt-json-authoring/references/industrial-authoring.md`

## 能做什么

- 从工作流设计和同版本 seed export 生成 FastGPT 应用 JSON。
- 修复损坏的 FastGPT 导出 JSON。
- 检查边、handle、引用、变量 key、HTTP 输出、知识库绑定、catch 分支。
- 沉淀可重复的 FastGPT JSON 生成流程。
- 支持真实导出中常见节点：
  `formInput`, `userSelect`, `ifElseNode`, `httpRequest468`, `variableUpdate`,
  `datasetSearchNode`, `textEditor`, `chatNode`, `answerNode`。
- 支持生产级关注点：
  token 脱敏、知识库重绑定、HTTP header 插值、form-data、动态输出、菜单回流、运行态变量。

## 适合谁

- 正在用 FastGPT / AIBuilder 搭复杂业务应用的人；
- 需要把画布应用沉淀成可版本管理 JSON 的团队；
- 想用 AI Agent 自动生成 FastGPT 应用，但不想赌随机 schema 的开发者；
- 需要检查、修复、重构 FastGPT 导出 JSON 的工程团队；
- 做 RAG、销售助手、客服助手、审批流、培训教练、知识库问答、多分支工作流的人。

## 目录结构

```text
skills/fastgpt-json-authoring/
  SKILL.md                         # skill 入口和执行协议
  agents/openai.yaml               # 可选 UI 元数据
  references/
    authoring-workflow.md          # 生成/修复工作流
    industrial-authoring.md        # 工业级生成原则
    json-schema.md                 # 实测导出结构说明
    node-templates.md              # 常见节点形状
    template-first-vs-export-calibrated.md
  scripts/
    fastgpt_canvas_inspect.py      # 确定性检查器

examples/
  hr-recruiting-assistant.json     # 通用示例应用

tests/
  fixtures/
  test_fastgpt_canvas_inspect.py
```

## 安装

把 `skills/fastgpt-json-authoring` 复制或软链到你的 AI Agent 平台的 skills 目录。

Codex 风格环境示例：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/fastgpt-json-authoring "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Claude Code、OpenClaw、Trae、CoStrict 或其他支持 skill 的平台，也可以使用同样的 skill 文件夹结构。保留 `references/` 和 `scripts/` 即可。

## 基本用法

让 Agent 使用这个 skill，并提供当前 FastGPT 环境导出的 seed JSON：

```text
Use fastgpt-json-authoring to generate a FastGPT app JSON.

Seed export: ./exports/minimal-current-version.json
Workflow:
- login
- permission check
- main menu
- customer search
- knowledge retrieval
- AI answer

HTTP API contract:
...
```

直接检查已有导出：

```bash
python3 skills/fastgpt-json-authoring/scripts/fastgpt_canvas_inspect.py app.json
python3 skills/fastgpt-json-authoring/scripts/fastgpt_canvas_inspect.py app.json --json
```

检查器是只读的，会报告：

- 节点/边/变量概况；
- 非法 edge handle；
- 找不到的节点、变量、输出引用；
- HTTP 节点缺失 URL/body/output/catch；
- `datasetSearchNode.datasets=[]`；
- 可疑菜单回流；
- 疑似未脱敏 token。

## 推荐生产流程

1. 从目标 FastGPT / AIBuilder 环境导出一个最小 seed app。
2. seed app 里包含目标应用需要的节点类型。
3. 脱敏 token、私有客户数据和内部 URL。
4. 写出节点 inventory 和主流程图。
5. 克隆 seed 节点形状，填入业务值和引用。
6. 在 nodeId、option key、output id 都固定后生成 edges。
7. 跑 inspector，修掉阻塞问题。
8. 导入 FastGPT 副本。
9. 重选知识库、模型、真实 token、API base URL 等环境绑定。
10. 预览验证成功路径、拒绝路径、API 失败路径、菜单/退出/重入路径。

## 交付状态怎么说

不要只因为 JSON 能解析就说“生产可用”。建议使用三个清晰状态：

| 状态 | 含义 |
| --- | --- |
| `static-validated` | inspector 已通过，或只剩明确记录的预期提醒。 |
| `import-validated` | FastGPT 已成功导入，画布能打开。 |
| `runtime-validated` | FastGPT 预览已经跑通过关键业务路径。 |

## 测试

```bash
python3 -m unittest discover -s tests
python3 -m py_compile skills/fastgpt-json-authoring/scripts/fastgpt_canvas_inspect.py
```

不需要第三方 Python 依赖。

## English Summary

FastGPT JSON Authoring Skill is a production-oriented, platform-neutral skill
package for generating, inspecting, repairing, and validating FastGPT / AIBuilder
workflow JSON exports.

It focuses on export-calibrated authoring: use real same-version FastGPT exports
as seed templates, compile workflows as explicit graph programs, run
deterministic inspection, and separate static validation from import/runtime
validation.

Compared with generic template-first JSON generators, this project is designed
to catch practical import, canvas-render, and preview-time issues that only show
up in real FastGPT deployments.

## License

Apache-2.0. See `LICENSE`.
