"""命令解析与图片处理工具，供各插件复用。"""
import base64
import json
import os
import re

import httpx
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.rule import Rule

_WIN_PATH = re.compile(r"^[A-Za-z]:[\\/]")
# 私聊里 @机器人 可能是字面文本（如 "@NAMEbot /echo 你好"），把开头的 @xxx 去掉
_AT_PREFIX = re.compile(r"^@\S+\s*")


def _cmd_and_arg(event: MessageEvent) -> tuple[str, str]:
    """/命令 参数 -> ("命令", "参数")，命令名统一小写。"""
    text = event.get_message().extract_plain_text().lstrip()
    text = _AT_PREFIX.sub("", text)
    if not text.startswith("/"):
        return "", ""
    body = text[1:]
    for sep in (" ", "\u3000"):
        if sep in body:
            name, _, arg = body.partition(sep)
            return name.lower(), arg.strip()
    return body.lower(), ""


def command_rule(name: str) -> Rule:
    """匹配 ``/name`` 或 ``/name 参数``（忽略 @机器人 带来的前导空白）。"""

    async def _rule(event: MessageEvent) -> bool:
        if event.get_type() != "message":
            return False
        return _cmd_and_arg(event)[0] == name

    return Rule(_rule)


def cmd_arg(event: MessageEvent) -> str:
    return _cmd_and_arg(event)[1]


def quoted_text(event: MessageEvent) -> str:
    """被引用（回复）的消息里的纯文本；没有引用/没有文字则返回空串。"""
    reply = getattr(event, "reply", None)
    if reply is None:
        return ""
    try:
        return (reply.message.extract_plain_text() or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def prompt_with_quote(event: MessageEvent) -> str:
    """把「命令参数」和「引用内容」合成 prompt。

    - 只发了参数：用参数
    - 只引用了消息：用引用内容
    - 两者都有：引用内容当素材，参数当要求
    """
    arg = cmd_arg(event)
    quote = quoted_text(event)
    if quote and arg:
        return f"引用的内容：\n{quote}\n\n我的要求：{arg}"
    return arg or quote


# 识图时统一追加的指令：按用户的问题作答，给具体结论，别编造
VISION_INSTRUCTION = (
    "你是识图助手。请先仔细观察图片，然后针对用户的问题作答，给出尽量具体、准确的结论。"
    "例如：\n"
    "- 问人物 / 角色：给出角色名，并指出出自哪部作品；\n"
    "- 问景点 / 地点：给出景点名称和所在的城市 / 国家；\n"
    "- 问物品 / 动植物 / 画作 / 食物等：给出具体名称或类别；\n"
    "- 问图中发生了什么 / 有什么：如实描述关键内容。\n"
    "如果无法确定，就明确说明不确定，不要编造。"
)


def _win_to_wsl(path: str) -> str:
    if _WIN_PATH.match(path):
        return f"/mnt/{path[0].lower()}{path[2:].replace(chr(92), '/')}"
    return path


def collect_image_segments(event: MessageEvent) -> list:
    """本消息里的图片；没有则取被引用消息里的图片。"""
    segs = [s for s in event.get_message() if s.type == "image"]
    if not segs and event.reply is not None:
        segs = [s for s in event.reply.message if s.type == "image"]
    return segs


async def image_segment_to_url(seg) -> str | None:
    """把图片段转成模型能吃的 url（http 直链，或 base64 data URI）。"""
    data = seg.data
    url = (data.get("url") or "").strip()
    if url.startswith("http"):
        return url
    raw_path = data.get("file") or url
    raw_path = raw_path.replace("file:///", "").replace("file://", "")
    path = _win_to_wsl(raw_path)
    if os.path.isfile(path):
        with open(path, "rb") as f:
            blob = f.read()
        ext = os.path.splitext(path)[1].lstrip(".").lower() or "jpeg"
        return f"data:image/{ext};base64,{base64.b64encode(blob).decode()}"
    return None


async def ai_chat_web(
    base_url: str,
    headers: dict,
    model_spec: str,
    input_items: list,
    instructions: str | None = None,
    thinking: str | None = "enabled",
    web_search: bool = True,
    timeout: int = 300,
) -> str:
    """走 /v1/responses 调用（这样才能启用模型服务的联网搜索 web_search）。

    流式收集 ``response.output_text.delta`` 拼出最终回答。
    """
    models = [m.strip() for m in str(model_spec).split(",") if m.strip()]
    last_err = "没有配置可用模型"
    for model in models:
        payload: dict = {"model": model, "stream": True, "input": input_items}
        if instructions:
            payload["instructions"] = instructions
        if thinking:
            payload["thinking"] = {"type": thinking}
        if web_search:
            payload["tools"] = [{"type": "web_search"}]
        text = ""
        done_text = ""
        err = ""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    base_url.rstrip("/") + "/responses",
                    headers=headers,
                    json=payload,
                ) as resp:
                    if resp.status_code != 200:
                        body = (await resp.aread()).decode(errors="replace")
                        last_err = f"HTTP {resp.status_code} {body[:200]}"
                        continue
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if not raw or raw == "[DONE]":
                            continue
                        try:
                            evt = json.loads(raw)
                        except ValueError:
                            continue
                        etype = evt.get("type") or ""
                        if etype == "response.output_text.delta":
                            text += evt.get("delta") or ""
                        elif etype == "response.output_text.done":
                            done_text = evt.get("text") or done_text
                        elif etype in ("response.failed", "response.error", "error"):
                            err = str(evt.get("error") or evt)[:200]
                        elif etype == "response.completed":
                            break
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            continue
        answer = (text or done_text).strip()
        if answer:
            return answer
        last_err = err or "模型没有返回内容"
    raise RuntimeError(last_err)
