"""图片识别：把打卡照片变成菜品候选。

走 OpenAI 兼容的 chat/completions 接口（当前配置指向 DeepSeek），
把图片以 data URI 塞进 image_url，模型返回 JSON。

设计要点：
- 只有配了 ``LLM_API_KEY`` 才启用；没配就返回 ``NO_PROVIDER``，前端降级成手动选菜
- 超时/网络错误一律当成「识别失败」，**不阻断打卡流程**
- 返回结构固定：``{"dishes": [{name, confidence, category}], "note": "..."}``
"""
from __future__ import annotations

import json
import re

from django.conf import settings

try:  # 只用标准库，少一个依赖
    import urllib.error
    import urllib.request
except ImportError:  # pragma: no cover
    urllib = None

SYSTEM_PROMPT = """你是校园食堂的菜品识别助手。用户会给你一张他吃的食物的照片。
请判断照片里是什么菜，并给出中文菜名。

只输出 JSON，不要 markdown 代码块，不要解释。格式：
{"dishes":[{"name":"菜名","confidence":0.9,"category":"盖饭"}],"note":"一句话描述"}

要求：
- 最多 3 个候选，按可能性从高到低
- name 用中国人日常叫法，例如「红烧肉盖饭」「兰州拉面」「麻辣香锅」
- category 从这些里选：盖饭 / 面食 / 小吃 / 火锅 / 快餐 / 热菜 / 饮品 / 其他
- 如果图里明显不是食物，返回 {"dishes":[],"note":"没有识别到食物"}
- confidence 用 0~1 的小数"""


class VisionError(Exception):
    """识别失败（网络/超时/模型报错），调用方按「识别不可用」处理。"""


def provider_ready() -> bool:
    return bool(getattr(settings, "LLM_API_KEY", ""))


def recognize(image: str, timeout: int | None = None) -> dict:
    """识别一张图片。

    ``image`` 可以是 ``data:image/...;base64,xxx`` 完整 URI，也可以是纯 base64。
    返回 ``{"dishes": [...], "note": "...", "provider": "deepseek"}``。
    """
    if not provider_ready():
        raise VisionError("未配置视觉模型（LLM_API_KEY 为空）")

    data_uri = image if image.startswith("data:") else f"data:image/jpeg;base64,{image}"

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "这是什么菜？按约定返回 JSON。"},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            },
        ],
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": 300,
        "stream": False,
    }

    req = urllib.request.Request(
        settings.LLM_BASE_URL.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {settings.LLM_API_KEY}")

    try:
        with urllib.request.urlopen(req, timeout=timeout or settings.LLM_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # 4xx/5xx
        detail = exc.read().decode("utf-8", "ignore")[:300]
        raise VisionError(f"模型接口返回 {exc.code}: {detail}") from exc
    except Exception as exc:  # 超时 / 网络不可达
        raise VisionError(f"调用模型失败: {exc}") from exc

    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise VisionError("模型返回里没有内容") from exc

    parsed = _parse_json(text)
    dishes = []
    for item in (parsed.get("dishes") or [])[:3]:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        try:
            confidence = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        dishes.append(
            {
                "name": name[:64],
                "confidence": round(max(0.0, min(1.0, confidence)), 2),
                "category": str(item.get("category") or "其他")[:16],
            }
        )

    return {
        "dishes": dishes,
        "note": str(parsed.get("note") or "")[:120],
        "provider": "llm",
        "model": body.get("model", ""),
    }


def _parse_json(text: str) -> dict:
    """模型偶尔会套 ```json 代码块或加前后缀，这里做容错。"""
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return {}
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
