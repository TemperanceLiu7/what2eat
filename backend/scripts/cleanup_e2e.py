"""一次性清理脚本：删掉 e2e / dbg 测试账号及其数据，把学籍释放回 seed 占位账号。

用法（在 backend/ 目录）：
    python scripts/cleanup_e2e.py
"""
import os
import sys
from pathlib import Path

import django

# 让脚本能 import 到上级目录的 config / core
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_dev")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from core.models import Checkin, Favorite, Like, Report, Vote, VoteRecord  # noqa: E402

User = get_user_model()

# 只删测试时自动生成的账号，admin 和 roster_* 学籍占位账号不动
PREFIXES = ("e2e_", "dbg_", "demo_", "ui_", "fin_", "diag_", "net_", "net2_", "test_", "ok_", "ra_", "rb_", "ra2", "rb2")

qs = User.objects.none()
for prefix in PREFIXES:
    qs = qs | User.objects.filter(username__startswith=prefix)

names = list(qs.values_list("username", flat=True))
print(f"待删除测试账号：{len(names)} 个 -> {names}")

Checkin.objects.filter(user__in=qs).delete()
VoteRecord.objects.filter(user__in=qs).delete()
Vote.objects.filter(creator__in=qs).delete()
Like.objects.filter(user__in=qs).delete()
Favorite.objects.filter(user__in=qs).delete()
Report.objects.filter(reporter__in=qs).delete()
print(f"删除用户：{qs.delete()}")

print("\n剩余用户：")
for u in User.objects.order_by("id"):
    print(f"  {u.username:<20} {u.name or '-':<8} {u.college or '-':<12} student_id={u.student_id or '-'}")
