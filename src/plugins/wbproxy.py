"""文本对话（服务地址与 key 从 .env 读取：WB_BASE_URL / WB_DS_KEY）

  @机器人 /ds    文本      -> 深度思考 + 联网搜索
  @机器人 /imgds [问题]    -> 看图（图片和指令一起发，或引用一张图片再发）

引用：引用（回复）一条消息再发指令，引用内容会当作 prompt / 图片素材。
"""
from collections import defaultdict, deque

from nonebot import get_plugin_config, on_message
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.rule import to_me
from pydantic import BaseModel

from src.plugins._common import (
    VISION_INSTRUCTION,
    ai_chat_web,
    cmd_arg,
    collect_image_segments,
    command_rule,
    image_segment_to_url,
    prompt_with_quote,
    quoted_text,
)


class Config(BaseModel):
    wb_base_url: str = "https://your-api.example/v1"
    wb_ds_key: str = ""
    wb_system: str = "你是一个 QQ 聊天机器人，用中文回复，语气自然简洁，别太啰嗦。"


cfg = get_plugin_config(Config)

# 文本指令 -> (key 字段名, 模型名)
TARGETS = {
    "ds": ("wb_ds_key", "deepseek-v4.1-flash"),
}

# 每个会话保留最近 20 条上下文
_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=20))


def _headers(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _make_text(cmd: str, keyname: str, model: str):
    matcher = on_message(rule=to_me() & command_rule(cmd), priority=10, block=True)

    @matcher.handle()
    async def _handle(event: MessageEvent):
        key = getattr(cfg, keyname)
        if not key:
            await matcher.finish(f"/{cmd} 还没配置 key")
        text = prompt_with_quote(event)
        # 带了图片（本消息附带，或引用的是一条没有文字的纯图片消息）却用了纯文本指令 -> 提示改用 /img
        if collect_image_segments(event) and not quoted_text(event):
            await matcher.finish(f"这是一张图片，看图请用 /img{cmd} [问题]")
        if not text:
            await matcher.finish(f"用法: /{cmd} 文本（也可以引用一条消息再发）")
        skey = f"{event.message_type}:{getattr(event, 'group_id', None) or event.user_id}"
        history = _history[skey]
        inputs = [
            {"role": m["role"], "content": [{"type": "input_text", "text": m["content"]}]}
            for m in history
        ]
        inputs.append({"role": "user", "content": [{"type": "input_text", "text": text}]})
        try:
            reply = await ai_chat_web(
                cfg.wb_base_url,
                _headers(key),
                model,
                inputs,
                instructions=cfg.wb_system,
                thinking="enabled",
            )
        except Exception as e:  # noqa: BLE001
            await matcher.finish(f"调用出错: {e}")
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": reply})
        await matcher.finish(reply)

    return matcher


def _make_vision(cmd: str, keyname: str, model: str):
    matcher = on_message(rule=to_me() & command_rule(cmd), priority=10, block=True)

    @matcher.handle()
    async def _handle(event: MessageEvent):
        key = getattr(cfg, keyname)
        if not key:
            await matcher.finish(f"/{cmd} 还没配置 key")
        segs = collect_image_segments(event)
        if not segs:
            await matcher.finish("没找到图片。把图片和指令一起发，或引用一张图片再发")
        urls = [u for u in [await image_segment_to_url(s) for s in segs[:1]] if u]
        if not urls:
            await matcher.finish("图片读取失败（拿不到图片地址）")
        question = cmd_arg(event) or quoted_text(event) or "请描述这张图片的内容。"
        content = [
            {"type": "input_text", "text": f"{VISION_INSTRUCTION}\n\n用户的问题：{question}"},
            {"type": "input_image", "image_url": urls[0]},
        ]
        try:
            answer = await ai_chat_web(
                cfg.wb_base_url,
                _headers(key),
                model,
                [{"role": "user", "content": content}],
                thinking="enabled",
                timeout=240,
            )
        except Exception as e:  # noqa: BLE001
            await matcher.finish(f"看图失败: {e}")
        await matcher.finish(answer)

    return matcher


for _name, (_keyname, _model) in TARGETS.items():
    _make_text(_name, _keyname, _model)
    _make_vision("img" + _name, _keyname, _model)
