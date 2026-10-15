# nonebot-qq-ai-bot

一个跑在 QQ 群里的 AI 机器人：**对话 + 深度思考 + 联网搜索 + 看图**。

基于 [NoneBot2](https://nonebot.dev/) + [OneBot V11](https://github.com/botuniverse/onebot-11)（通过 [NapCat](https://github.com/NapNeko/NapCatQQ) 接入 QQ）。

## ✨ 特性

- **文本对话**：深度思考 + 联网搜索
- **看图**：发一张图片即可识图
- **引用（回复）消息**：把被引用的文字当题目、被引用的图片当素材，再配上你的要求
- **纯配置驱动**：服务地址和 key 都写在 `.env` 里，换服务不用改代码
- **群聊小功能**：说脏话自动"古诗劝导"、组队计数等

## 📖 指令表

> 群聊里要先 `@机器人`，私聊直接发。

| 指令 | 作用 |
|---|---|
| `/ds 内容` | 文本对话（深度思考 + 联网搜索） |
| `/imgds` + 图片 | 看图 / 识图 |
| `/help` | 查看完整指令表 |

> 支持**引用（回复）一条消息**再发指令：引用文字当题目，引用图片当素材。
> 完整的实时指令清单以 `/help` 的输出为准。

## 🏗️ 架构

```
┌──────────────┐        QQNT 协议        ┌──────────────────────┐
│  QQ 客户端    │ ◀────────────────────▶ │ NapCat               │
└──────────────┘                        └──────────┬───────────┘
                                                   │ 反向 WebSocket
                                                   │ (OneBot V11)
                                                   ▼
                                        ┌──────────────────────┐
                                        │ NoneBot2 (本仓库)     │
                                        │  0.0.0.0:8080        │
                                        │  src/plugins/*.py    │
                                        └──────────┬───────────┘
                                                   │ HTTP
                                                   ▼
                                        ┌──────────────────────┐
                                        │ 模型服务             │
                                        └──────────────────────┘
```

NapCat 和 NoneBot2 **不要求在同一台机器**：NapCat 在哪里登录 QQ，就让它反向连到 NoneBot 的 `ws://<NoneBot地址>:8080/onebot/v11/ws` 即可。

## 🚀 快速开始

### 1. 环境要求

- Python **3.11+**
- 一个 QQ 小号（建议不要用主号）
- [NapCat](https://github.com/NapNeko/NapCatQQ) 已安装并能登录

### 2. 安装

```bash
git clone https://github.com/YoimiyaSama1/nonebot-qq-ai-bot.git
cd nonebot-qq-ai-bot

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置

```bash
cp .env.example .env
vim .env          # 填 ONEBOT_ACCESS_TOKEN、SUPERUSERS，以及你要用的模型 key
```

> ⚠️ `.env` 里全是密钥，已在 `.gitignore` 中忽略，**千万不要提交**。

### 4. 启动

```bash
python bot.py
# 或者用自带的脚本
./manage.sh start      # start | stop | restart | status | log
```

### 5. 接入 NapCat

在 NapCat 的「网络配置 → 新建 → WebSocket 客户端」里填：

- URL：`ws://<NoneBot 所在地址>:8080/onebot/v11/ws`
- Token：与 `.env` 里的 `ONEBOT_ACCESS_TOKEN` **完全一致**

连上后，在群里 `@机器人 /help` 就能看到指令表。

## ⚙️ 配置说明

`bot.py` 会自动读取 `.env`，各插件通过 `get_plugin_config` 取自己的那部分配置。

| 变量 | 说明 |
|---|---|
| `DRIVER` | 反向 WS 必须用 `~fastapi` |
| `HOST` / `PORT` | NoneBot 监听地址，默认 `0.0.0.0:8080` |
| `ONEBOT_ACCESS_TOKEN` | 与 NapCat 的 token 一致 |
| `SUPERUSERS` | 超管 QQ 号，JSON 数组格式 |
| `WB_*` | 文本对话 / 看图所用的服务地址与 key |

**模型降级链**：模型名支持逗号分隔写多个，例如 `model-a,model-b` ——
前一个报「访问量过大」会自动换下一个。

**联网搜索**：`_common.py` 里的 `ai_chat_web()` 走 `/v1/responses` 接口（不是
`/v1/chat/completions`），因为联网工具只在 `/v1/responses` 上生效。

## 📁 目录结构

```
.
├── bot.py                    # 入口：初始化 NoneBot + 注册适配器 + 加载插件
├── manage.sh                 # 启停脚本
├── pyproject.toml
├── requirements.txt
├── .env.example              # 配置模板（复制成 .env 再用）
└── src/plugins/
    ├── _common.py            # 公共工具：命令解析、引用处理、模型调用
    ├── wbproxy.py            # /ds 文本对话、/imgds 看图
    ├── help.py               # /help
    ├── echo.py               # /echo
    ├── timi.py               # /timi
    └── civil.py              # 脏话 → 古诗（被动）
```

> 以 `_` 开头的文件不会被 NoneBot 当成插件加载（`_common.py` 是纯工具库）。

> 📌 新增或修改指令后，记得同步 `help.py` 里的 `SECTIONS`，否则 `/help` 会不同步。

## 📝 说明

- 本项目**不内置任何密钥**，需要你自备模型服务。
- 命令解析是自己写的规则（见 `_common.py` 的 `command_rule`），没有用 NoneBot 的 `on_command`——这样能统一处理「群里 `@机器人` + 私聊」两种消息形态。

## 📄 License

[MIT](LICENSE)
