"""图片写入：前端 ``<input type=file>`` 读出来的 base64 data URL 直接落盘。

前端打卡时把图片转成 ``data:image/jpeg;base64,....`` 放进 JSON body，
这里负责解码、校验（大小 / 真实图片格式）并包成 Django ``ContentFile``，
模型保存时由 ``ImageField(upload_to=...)`` 放到 ``MEDIA_ROOT``。
"""
from __future__ import annotations

import base64
import binascii
import uuid
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile

from .responses import INVALID_DATA, ApiError

# Pillow 识别出的格式 → 文件后缀
_EXT_BY_FORMAT = {
    "JPEG": "jpg",
    "PNG": "png",
    "GIF": "gif",
    "WEBP": "webp",
    "BMP": "bmp",
    "TIFF": "tiff",
}
_ALLOWED_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}


def _probe_format(raw: bytes) -> str:
    """用 Pillow 校验是不是真图片，返回格式名（如 JPEG）。"""
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow 在 requirements 里
        return "JPEG"
    try:
        with Image.open(BytesIO(raw)) as img:
            fmt = (img.format or "").upper()
            img.verify()
    except Exception as exc:  # noqa: BLE001 - 任何解码失败都算非法图片
        raise ApiError(INVALID_DATA, "图片解析失败，请换一张图片再试") from exc
    if fmt not in _ALLOWED_FORMATS:
        raise ApiError(INVALID_DATA, "只支持 JPG / PNG / GIF / WEBP 图片")
    return fmt


def save_base64_image(value: str | None, name_hint: str = "upload") -> ContentFile | None:
    """把 data URL / 纯 base64 转成待保存的图片文件。

    返回 ``None`` 表示「这次没有新图片」：
    - 空值 / None
    - 已经是 http(s) 或 /media/ 开头的地址（说明是旧图，不重复落盘）
    """
    if not value or not isinstance(value, str):
        return None

    raw_value = value.strip()
    if not raw_value:
        return None
    lowered = raw_value.lower()
    if lowered.startswith(("http://", "https://", "/media/", "/static/")):
        return None

    if lowered.startswith("data:"):
        header, _, payload = raw_value.partition(",")
        if ";base64" not in header.lower():
            raise ApiError(INVALID_DATA, "图片格式不支持，请上传图片文件")
    else:
        payload = raw_value  # 允许直接传裸 base64

    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ApiError(INVALID_DATA, "图片数据损坏，请重新选择图片") from exc

    if not raw:
        return None

    max_bytes = int(getattr(settings, "IMAGE_MAX_BYTES", 5 * 1024 * 1024))
    if len(raw) > max_bytes:
        raise ApiError(
            INVALID_DATA, f"图片太大，请压缩到 {max_bytes // (1024 * 1024)}MB 以内"
        )

    fmt = _probe_format(raw)
    ext = _EXT_BY_FORMAT.get(fmt, "jpg")
    filename = f"{name_hint}-{uuid.uuid4().hex[:16]}.{ext}"
    return ContentFile(raw, name=filename)
