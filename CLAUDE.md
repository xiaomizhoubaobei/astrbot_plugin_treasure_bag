# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

这是 AstrBot 插件 **百宝袋（treasure_bag_plugin）**，通过 `@filter.command` 注册一组娱乐/查询指令，每个指令直接调用第三方 HTTP API 并把结果回给聊天用户。

- 插件根目录就是本仓库根目录，`main.py` 必须位于根目录（AstrBot 插件加载约定）。
- `AGENTS.md` 是更高优先级的代理协作规范（中文提交信息、GPG 签名、PR/镜像同步、记忆库等），动 Git/流程前先读它。注意其第 10 章描述的是另一个插件（`astrbot_plugin_models_ai`）的目录与工具链，与当前仓库不符；代码结构以本文件为准。
- 根目录的 `astrbot/` 与 `AstrBot/` 是 `.gitignore` 掉的 AstrBot 框架副本/克隆（CNB 开发环境用），**不是插件源码**，不要修改或提交。测试也不依赖它们：`tests/conftest.py` 自行注入最小 AstrBot 桩。

## 常用命令

```bash
# 安装依赖（运行依赖 + 测试工具）
pip install -r requirements.txt -r requirements-dev.txt

# 跑全部测试
python -m pytest -q

# 只跑单个测试
python -m pytest tests/test_main.py::test_commands_registered -q

# 跑测试并生成 coverage.xml（CI 口径）
python -m tests.run_coverage
python -m tests.run_coverage -- -k weather      # "--" 之后透传给 pytest

# 代码规范检查（唯一实际生效的 lint 配置）
pre-commit run --all-files

# 构建可上传的插件 zip（输出 <metadata name>.zip）
python build_release.py --output dist.zip
```

说明：

- CI 覆盖 Python 3.12–3.15（`coverage.yml`），代码按 3.12+ 编写。
- **不要**用 `coverage run -m pytest` 代替 `tests/run_coverage.py`：必须在 `tests/conftest.py` 建立 `treasure_bag` 包视图和 AstrBot 桩之后再启动 Coverage，否则覆盖率口径为空（原因写在脚本 docstring 里）。
- `.pre-commit-config.yaml` 实际只有 `ruff` + `ruff-format` + 基础文件检查（`.ruff.toml` 仅选 `E4/E7/E9/F`）。AGENTS.md 中提到的 black/flake8/mypy/pylint 配置在本仓库并不存在，不要按那套去修 lint。
- `requirements.txt` 里的 `ruff`、`sqlalchemy`、`pymysql` 目前不被插件源码引用；真正的运行依赖是 `aiohttp` 与 `httpx`。

## 代码架构

```
AstrBot 消息事件
      │
      ▼
main.py  TreasureBagPlugin(Star)
      │  按命令名把 event 分发给对应 handler
      ├── handlers/*          一指令一模块，直接调用第三方 API
      ├── baidu/beauty_handler.py   颜值评分（百度人脸识别）
      └── baidu/baidu_auth.py       百度 access_token 单例与缓存
```

### 入口与命令注册

`main.py` 的 `TreasureBagPlugin` 是唯一注册点。每个命令方法只是薄包装：

- 一次性结果（`hitokoto`、`bdrate_beauty`）用 `yield await handler(event)`，对应 handler 直接 `return event.plain_result(...)`；
- 可能多次输出/需要延后产出（其余命令）用 `async for result in handler(event): yield result`，对应 handler 是异步生成器（`yield event.plain_result(...)` / `yield event.image_result(...)`）。

注册名以 `main.py` 为准：`hitokoto`、`bdrate_beauty`、`kog_info`、`handwrite`、`beauty_img`（3 个别名）、`sad-word`（4 个别名）、`今日运势`（别名 `星座运势`，通过关键字参数 `xingzuo_name` 接收星座）、`weather`（别名 `天气`）、`treasurebag-help`。

新增指令需要：在 `handlers/` 写 handler → 在 `main.py` 注册 `@filter.command` → 在 `help_command` 的帮助文本中补充 → 同步 `tests/test_main.py` 的注册/别名断言。

### Handler 约定

- 每个 handler 第一参数是 `AstrMessageEvent`，日志统一用 `from astrbot.api import logger`，不用 `print`。
- HTTP 调用要么 `aiohttp.ClientSession`，要么 `httpx.AsyncClient`；每个 handler 内自行创建会话（项目没有共享会话层）。
- 所有异常都被捕获并转成中文 `event.plain_result(...)` 回包；上游错误码（百度 `error_code` 等）在 handler 内翻译成用户可读文案。
- 参数解析有两套写法，改动时保持现状：
  - `utils/command_utils.extract_command_arg(event, keyword)`：拼接所有文本段，匹配 `/cmd ` 或 `cmd `（大小写不敏感），供 `handwrite`、`kog_info` 使用；
  - `weather` 直接用 `event.message_str.split(" ", 1)`；
  - `今日运势` 由 AstrBot 的 `*, xingzuo_name` 关键字参数注入。

### 百度认证与颜值评分

- `baidu/baidu_auth.py` 有模块级单例 `baidu_auth_manager`；`TreasureBagPlugin.__init__` 调用 `init_baidu_credentials(config)` 注入凭证。测试用 autouse fixture 在每个用例前后重置该单例，避免状态串扰。
- token 缓存在内存中，用 `asyncio.Lock` 保证并发安全，剩余有效期不足 1 小时才刷新。
- `baidu/beauty_handler.py` 的链路：取消息里的 `Image` 组件 → 下载图片（会解包 QQ `multimedia.nt.qq.com.cn` 的 `url=` 参数）→ base64 → 调百度人脸检测（`beauty/age/gender/emotion/...`）→ 拼装多段文本报告。报告格式化逻辑集中在 `generate_face_analysis_report`，改文案/字段时优先改它。

### 配置

- 配置 schema 在 `_conf_schema.json`，代码用**扁平键**读取：`config.get("baidu_api_key")`、`config.get("baidu_secret_key")`。README 里的 `[baidu] api_key = ...` 嵌套写法已过时，不要照抄。
- `aliyun_access_key_id/secret` 与 `admins` 当前没有任何代码使用，属于预留/历史字段。
- 密钥只能来自 AstrBot 插件配置，禁止写进源码、测试或提交记录。

### 构建与发布

- `build_release.py` 按白名单收集文件：根目录的 `__init__.py`、`main.py`、`metadata.yaml`、`requirements.txt`、`LICENSE`、`README.md`、`CHANGELOG.md`、`logo.png`、`build_release.py`，以及 `PACKAGE_DIRS = ("handlers", "baidu", "config", "utils")` 下所有 `*.py`。**新增顶层目录/包时必须同步改 `PACKAGE_DIRS` 和 `required` 清单**，否则发布包缺文件。
- `release.yml` 由 GitHub 镜像仓库的 `v*` tag 触发（CNB 只同步 `main`，不搬 tag）。打 tag 前必须先改 `metadata.yaml` 的 `version` 并合入，且 tag 名必须等于 `v<version>`；同时整理 `CHANGELOG.md`。
- 发布构建侧 Python 固定 `3.13`（`ci-evidence-pack` 的硬要求），与插件运行版本是两套约束，不要“统一”回 3.12。

### CI 与仓库协作

- CNB（`.cnb.yml`）：PR 在 CNB 侧跑门禁——安装依赖 → `pre-commit run --all-files`（失败重试一次）→ `python -m tests.run_coverage` 并转 lcov 上报；push 到 `main` 仅用 `git-sync` 同步到 GitHub 镜像 `xiaomizhoubaobei/astrbot_plugin_treasure_bag`。
- GitHub Actions：`coverage.yml` 在 3.12–3.15 跑测试，只有 3.12 上报 Codecov（`CODECOV_TOKEN` 未配置时自动跳过）；另有 CodeQL、DevSkim、secret-scanning、依赖审计、Scorecard、tfsec、stale 等安全工作流。
- 按 AGENTS.md：变更走 PR，不直接推 `main`；提交信息必须是中文 Conventional Commits；**每次 `git commit` 前先执行 `bash install_gpg_keys.sh`**。本仓库 `.cnb.yml` 含 GitHub 镜像同步配置，因此按 AGENTS.md §3.5，CNB 建 PR 时还应在 GitHub 镜像仓库创建同内容 PR。

## 测试约定

- `pytest.ini` 开启 `asyncio_mode = auto`，异步测试直接写 `async def test_...`，不需要 `@pytest.mark.asyncio`。
- `tests/conftest.py` 会：注入 `astrbot.*` 最小桩、把仓库根挂载为 `treasure_bag` 包、提供 `make_event`、`patch_aiohttp`、`patch_httpx` 三个 fixture，并自动重置百度认证单例。测试统一 `from treasure_bag.<module> import ...`，不要用相对导入或仓库目录名导入。
- 网络请求一律用 `tests/fakes.py` 的 `FakeAiohttpSession` / `FakeHttpxClient` / `FakeResponse` 替换，不访问真实 API。新增 handler 时照此补离线用例。

## 已知文档漂移（改文档前先核对代码）

- README 的命令列表写的是 `/测颜值`、`/王者`，实际注册名是 `/bdrate_beauty`、`/kog_info`；别名与帮助文本也会随 `main.py` 变化。
- README 的配置示例是嵌套 `[baidu]`，实际读取的是扁平键。
- AGENTS.md 第 10 章及 10.7 节的工具链描述针对另一个插件（含 `src/` 布局、black/flake8/mypy 等），与本仓库不符；本仓库没有 `src/`，lint 只有 ruff。
