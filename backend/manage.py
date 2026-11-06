#!/usr/bin/env python
"""Django 命令行入口。

默认加载 ``config.settings_dev``（SQLite，clone 下来就能跑）；
``DJANGO_ENV=prod`` 时切到 ``config.settings_prod``（MySQL + 强制关闭 DEBUG）。
显式设置 ``DJANGO_SETTINGS_MODULE`` 时以它为准，方便 CI / 自定义部署。
"""
import os
import sys


def _settings_module() -> str:
    explicit = os.environ.get("DJANGO_SETTINGS_MODULE")
    if explicit:
        return explicit
    env = os.environ.get("DJANGO_ENV", "dev").strip().lower()
    return "config.settings_prod" if env in {"prod", "production"} else "config.settings_dev"


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", _settings_module())
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - 只在没装依赖时触发
        raise ImportError(
            "无法导入 Django。请先安装依赖：\n"
            "  python -m pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
