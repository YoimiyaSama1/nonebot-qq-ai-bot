"""@机器人 /timi  -> 群里的王者荣耀组队邀请计数

- 第 1 个人发:  有人发起了王者荣耀邀请，目前人数1/5
- 之后每多一个人 +1（同一个人重复发不重复计数）
- 第 5 个人发后: 王者荣耀车队已满！ 之后一直回这句
- 距离发起超过 1 小时后自动重置为初始状态
"""
import time

from nonebot import on_message
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.rule import to_me

from src.plugins._common import command_rule

SESSION_TTL = 3600  # 1 小时
MAX_PEOPLE = 5

# group_id -> {"users": list[int], "start": float}
_sessions: dict[int, dict] = {}

# 群里的游戏指令，不强制 @（私聊里会提示去群里用）
timi = on_message(rule=command_rule("timi"), priority=10, block=True)


def join(group_id: int, uid: int, now: float | None = None) -> str:
    """返回该回给用户的文案。"""
    now = time.time() if now is None else now
    session = _sessions.get(group_id)
    if session is None or now - session["start"] > SESSION_TTL:
        # 没有车队，或已超过 1 小时 -> 开启新的一轮
        session = {"users": [], "start": now}
        _sessions[group_id] = session

    if uid not in session["users"]:
        session["users"].append(uid)

    count = len(session["users"])
    if count >= MAX_PEOPLE:
        return "王者荣耀车队已满！"
    return f"有人发起了王者荣耀邀请，目前人数{count}/{MAX_PEOPLE}"


@timi.handle()
async def handle_timi(event: MessageEvent):
    if event.message_type != "group":
        await timi.finish("请在群里使用 /timi")
    await timi.finish(join(event.group_id, event.user_id))
