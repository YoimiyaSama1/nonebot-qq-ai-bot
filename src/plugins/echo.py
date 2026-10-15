"""@机器人 /echo 文本  -> 原样回复文本"""
from nonebot import on_message
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.rule import to_me

from src.plugins._common import cmd_arg, command_rule

echo = on_message(rule=to_me() & command_rule("echo"), priority=5, block=True)


@echo.handle()
async def handle_echo(event: MessageEvent):
    text = cmd_arg(event)
    await echo.finish(text or "用法: /echo 文本")
