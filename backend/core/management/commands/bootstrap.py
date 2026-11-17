"""``python manage.py bootstrap`` —— 云端首次启动的一键初始化（幂等，可重复执行）。

Render 免费档没有 Shell / 一次性任务，`migrate` 之后没有任何入口再补数据，
所以把「演示数据 + 学籍 + 后台账号」收敛成一个命令，挂到 startCommand 里：

    python manage.py migrate --no-input && python manage.py bootstrap && gunicorn ...

做的事：
1. 调 ``seed``：6 个档口 / 16 道菜 / 3 条学籍占位账号（按名字 upsert，重复执行不产生脏数据）
2. 按环境变量建后台账号（未设置 ``ADMIN_PASSWORD`` 就跳过，避免线上出现默认弱口令）

环境变量：
    ADMIN_USERNAME   后台账号名，默认 admin
    ADMIN_PASSWORD   后台密码；为空则跳过创建
"""
from __future__ import annotations

import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.models import User


class Command(BaseCommand):
    help = "初始化演示数据与后台账号（幂等，供云端部署时自动执行）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-admin",
            action="store_true",
            help="只补演示数据，不创建后台账号",
        )
        parser.add_argument(
            "--skip-seed",
            action="store_true",
            help="只处理后台账号，不导入演示数据",
        )

    def handle(self, *args, **options):
        if not options["skip_seed"]:
            self.stdout.write(self.style.MIGRATE_HEADING("[1/2] 导入演示数据"))
            call_command("seed", stdout=self.stdout, stderr=self.stderr)
        else:
            self.stdout.write("跳过演示数据")

        if options["skip_admin"]:
            return

        self.stdout.write(self.style.MIGRATE_HEADING("[2/2] 后台账号"))
        username = (os.environ.get("ADMIN_USERNAME") or "admin").strip()
        password = os.environ.get("ADMIN_PASSWORD") or ""

        existing = User.objects.filter(username=username).first()
        if existing:
            # 已存在就只补齐权限，不改密码（避免每次部署把人工改过的密码冲掉）
            changed = []
            if not existing.is_superuser:
                existing.is_superuser = True
                changed.append("is_superuser")
            if not existing.is_staff:
                existing.is_staff = True
                changed.append("is_staff")
            if changed:
                existing.save(update_fields=changed)
                self.stdout.write(f"  已存在账号 {username}，补齐权限：{', '.join(changed)}")
            else:
                self.stdout.write(f"  已存在账号 {username}，跳过")
            return

        if not password:
            self.stdout.write(
                self.style.WARNING(
                    f"  未设置 ADMIN_PASSWORD，跳过后台账号创建（需要后台时在环境变量里补上）"
                )
            )
            return

        User.objects.create_superuser(
            username=username,
            password=password,
            email=os.environ.get("ADMIN_EMAIL", ""),
            name="管理员",
            role=User.Role.ADMIN,
        )
        self.stdout.write(self.style.SUCCESS(f"  已创建后台账号 {username}"))
