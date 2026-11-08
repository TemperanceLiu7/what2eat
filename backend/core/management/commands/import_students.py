"""把学校导出的学籍 CSV 导入为「学籍占位账号」。

用法（在 backend/ 目录）：

    python manage.py import_students "C:\\path\\to\\学籍表.csv"
    python manage.py import_students "学籍表.csv" --reset   # 先清掉旧的 roster_* 占位账号

CSV 需要表头：学号,姓名,班级,学院（列顺序无所谓，按表头取值）。
学籍数据在库里以「不可登录的占位账号」形式存在（username=roster_<学号>），
学生本人注册后通过 /api/auth/bind-student/ 核验，核验通过时占位账号被删除、学号转移过去。
"""
from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import User

REQUIRED_COLUMNS = {"学号", "姓名", "学院"}


class Command(BaseCommand):
    help = "导入学籍 CSV（学号/姓名/班级/学院），生成用于核验的占位账号"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="学籍 CSV 文件路径")
        parser.add_argument(
            "--reset",
            action="store_true",
            help="导入前删除所有 roster_* 占位账号（已被真实用户绑定的不受影响）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="只解析不写库，用来先看看数据对不对",
        )

    def handle(self, *args, **options):
        path = Path(options["csv_path"])
        if not path.is_file():
            raise CommandError(f"找不到文件：{path}")

        rows = self._read_csv(path)
        self.stdout.write(f"解析到 {len(rows)} 条学籍记录")
        self.stdout.write(f"示例：{rows[0] if rows else '（空）'}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("--dry-run：未写入数据库"))
            return

        with transaction.atomic():
            if options["reset"]:
                deleted, _ = User.objects.filter(username__startswith="roster_").delete()
                self.stdout.write(f"已清理旧占位账号：{deleted} 条")

            created = updated = skipped = 0
            for item in rows:
                sid = item["student_id"]
                username = f"roster_{sid}"

                # 该学号已经绑在某个真实账号上（学生本人已核验过），跳过
                bound = (
                    User.objects.filter(student_id=sid)
                    .exclude(username__startswith="roster_")
                    .exists()
                )
                if bound:
                    self.stdout.write(
                        self.style.WARNING(f"  跳过 {sid}（{item['name']}）：该学号已被真实账号绑定")
                    )
                    skipped += 1
                    continue

                user, is_new = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "student_id": sid,
                        "name": item["name"],
                        "college": item["college"],
                        "status": User.Status.NORMAL,
                    },
                )
                if is_new:
                    user.set_unusable_password()  # 占位账号：不可登录，只作为学籍名单
                    user.save(update_fields=["password"])
                    created += 1
                else:
                    changed = False
                    for field, value in (
                        ("student_id", sid),
                        ("name", item["name"]),
                        ("college", item["college"]),
                    ):
                        if getattr(user, field) != value:
                            setattr(user, field, value)
                            changed = True
                    if changed:
                        user.save(update_fields=["student_id", "name", "college"])
                        updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"导入完成：新增 {created}，更新 {updated}，跳过 {skipped}，"
                f"库中学籍总数 {User.objects.filter(username__startswith='roster_').count()}"
            )
        )
        colleges = (
            User.objects.filter(username__startswith="roster_")
            .values_list("college", flat=True)
            .distinct()
        )
        self.stdout.write(f"涉及学院：{', '.join(sorted({c for c in colleges if c}))}")

    # ------------------------------------------------------------------
    @staticmethod
    def _read_csv(path: Path) -> list[dict]:
        raw = path.read_bytes()
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:  # pragma: no cover
            raise CommandError("无法识别文件编码，请另存为 UTF-8 或 GBK")

        reader = csv.DictReader(text.splitlines())
        header = {(h or "").strip() for h in (reader.fieldnames or [])}
        missing = REQUIRED_COLUMNS - header
        if missing:
            raise CommandError(f"CSV 缺少必需列：{'、'.join(sorted(missing))}；实际表头：{sorted(header)}")

        rows: list[dict] = []
        for raw_row in reader:
            row = {(k or "").strip(): (v or "").strip() for k, v in raw_row.items()}
            student_id = row.get("学号", "")
            name = row.get("姓名", "")
            college = row.get("学院", "")
            if not student_id or not name:
                continue  # 空行 / 合计数行
            rows.append(
                {
                    "student_id": student_id,
                    "name": name,
                    "class_name": row.get("班级", ""),
                    "college": college,
                }
            )
        if not rows:
            raise CommandError("CSV 里没有有效的学籍记录")
        return rows
