"""@机器人 /help  -> 显示当前所有可用指令

【维护提示】新增/删除指令后，请同步修改下面的 SECTIONS（改完重启 qqbot 生效）。
各指令的来源插件：
  wbproxy.py  -> /ds 文本对话、/imgds 看图
  echo.py     -> /echo
  timi.py     -> /timi
  civil.py    -> 群里脏话自动 @+古诗（被动触发）
"""
from nonebot import on_message
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.rule import to_me

from src.plugins._common import command_rule

help_cmd = on_message(rule=to_me() & command_rule("help"), priority=5, block=True)

HEADER = "📖 NAMEbot 指令表（群里要先 @ 我，私聊直接发）"

# ===== 指令表：在这里登记（顺序即展示顺序，按性能从高到低排）=====
SECTIONS: list[tuple[str, list[str]]] = [
    ("AI 对话 · 深度思考 + 联网搜索", [
        "/ds 内容　—　也可以引用一条消息再发",
    ]),
    ("看图", [
        "/imgds [问题]　—　图片和指令一起发，或引用一张图片再发",
    ]),
    ("其他", [
        "/echo 文本　—　原样复述",
        "/timi　—　组队计数（仅群聊，无需 @）",
        "/help　—　显示本表",
    ]),
    ("自动触发", [
        "群里有人说脏话　→　@ 他并附一句古诗",
    ]),
]


def render() -> str:
    """拼出帮助文本。"""
    lines = [HEADER]
    for title, items in SECTIONS:
        lines.append("")
        lines.append(f"【{title}】")
        lines.extend(f"· {item}" for item in items)
    return "\n".join(lines)


@help_cmd.handle()
async def handle_help(event: MessageEvent):
    await help_cmd.finish(render())
