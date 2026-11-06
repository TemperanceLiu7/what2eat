"""``python manage.py seed`` —— 导入演示数据。

内容（与前端 ``src/data/db.js`` 的演示数据一致，方便前后端对照）：
- 6 个档口（3 食堂 + 1 饭店 + 1 外卖 + 1 夜市）
- 16 个菜品
- 3 条学籍（用于 ``/api/auth/bind-student/`` 三重核验）

用法::

    python manage.py seed                # 幂等导入，已存在的不动
    python manage.py seed --reset        # 先清掉演示档口/菜品/学籍再导入
    python manage.py seed --admin        # 额外建一个后台账号 admin / admin123456

注意：``--reset`` 只删除本命令自己造的数据（按名字匹配），不会碰真实用户内容。
"""
from __future__ import annotations

import os

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Dish, Shop, User

# name / type / location
SHOPS: list[dict] = [
    {"name": "一食堂·三层小炒", "type": Shop.Type.CANTEEN, "location": "东区一食堂 3F"},
    {"name": "二食堂·麻辣香锅", "type": Shop.Type.CANTEEN, "location": "西区二食堂 2F"},
    {"name": "三食堂·兰州拉面", "type": Shop.Type.CANTEEN, "location": "南区三食堂 1F"},
    {"name": "西门鸡公煲", "type": Shop.Type.RESTAURANT, "location": "西门美食街"},
    {"name": "阿铭烤肉饭", "type": Shop.Type.TAKEOUT, "location": "外卖 · 约 30 分钟"},
    {"name": "夜市·烤冷面", "type": Shop.Type.NIGHT, "location": "北门夜市 18:00-23:00"},
]

# shop 用 SHOPS 下标；字段名对齐 Dish 模型
DISHES: list[dict] = [
    {"shop": 0, "name": "鱼香肉丝盖饭", "price": "12.00", "category": "盖饭",
     "description": "微辣，下饭神器", "likes": 36, "favorites": 12},
    {"shop": 0, "name": "番茄炒蛋盖饭", "price": "10.00", "category": "盖饭",
     "description": "酸甜口，永远不会错", "likes": 28, "favorites": 9},
    {"shop": 0, "name": "糖醋里脊", "price": "16.00", "category": "热菜",
     "description": "外酥里嫩，配米饭", "likes": 41, "favorites": 15},
    {"shop": 0, "name": "手工水饺（12 只）", "price": "14.00", "category": "面食",
     "description": "白菜猪肉，现包", "likes": 25, "favorites": 6},
    {"shop": 1, "name": "麻辣香锅（微辣）", "price": "18.00", "category": "香锅",
     "description": "自选配菜，一碗抵三菜", "likes": 52, "favorites": 21},
    {"shop": 1, "name": "冒菜", "price": "15.00", "category": "冒菜",
     "description": "一个人的火锅", "likes": 33, "favorites": 10},
    {"shop": 2, "name": "牛肉拉面", "price": "13.00", "category": "面食",
     "description": "一清二白三红四绿", "likes": 47, "favorites": 14},
    {"shop": 2, "name": "干拌面", "price": "11.00", "category": "面食",
     "description": "加个蛋更香", "likes": 22, "favorites": 6},
    {"shop": 3, "name": "鸡公煲（小份）", "price": "38.00", "category": "火锅",
     "description": "两人份，越煮越入味", "likes": 29, "favorites": 17},
    {"shop": 3, "name": "干锅花菜", "price": "22.00", "category": "热菜",
     "description": "配米饭一流", "likes": 18, "favorites": 5},
    {"shop": 4, "name": "烤肉饭 + 温泉蛋", "price": "19.00", "category": "快餐",
     "description": "招牌，酱汁给得足", "likes": 63, "favorites": 25},
    {"shop": 4, "name": "照烧鸡腿饭", "price": "18.00", "category": "快餐",
     "description": "甜口，适合不想吃辣", "likes": 44, "favorites": 13},
    {"shop": 4, "name": "咖喱牛肉饭", "price": "22.00", "category": "快餐",
     "description": "微辣，咖喱浓", "likes": 31, "favorites": 8},
    {"shop": 5, "name": "烤冷面（加蛋加肠）", "price": "9.00", "category": "小吃",
     "description": "夜市顶流，排队 5 分钟", "likes": 58, "favorites": 19},
    {"shop": 5, "name": "铁板鱿鱼", "price": "15.00", "category": "小吃",
     "description": "现烤，加辣更香", "likes": 26, "favorites": 7},
    {"shop": 5, "name": "炸串拼盘", "price": "12.00", "category": "小吃",
     "description": "十串任选", "likes": 34, "favorites": 11},
]

# 学籍名单：学号 + 姓名 + 学院，三重核验的数据源
ROSTER: list[dict] = [
    {"student_id": "20230001", "name": "张同学", "college": "计算机学院"},
    {"student_id": "20230002", "name": "李同学", "college": "外国语学院"},
    {"student_id": "20230003", "name": "王同学", "college": "机械工程学院"},
]

DEMO_ADMIN_USERNAME = "admin"
DEMO_ADMIN_PASSWORD = os.environ.get("DEMO_ADMIN_PASSWORD", "admin123456")


class Command(BaseCommand):
    help = "导入演示数据：6 个档口 + 16 个菜品 + 3 条学籍"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="先删除本命令导入过的档口/菜品/学籍占位账号，再重新导入",
        )
        parser.add_argument(
            "--admin",
            action="store_true",
            help=f"额外创建后台账号 {DEMO_ADMIN_USERNAME}（密码见 DEMO_ADMIN_PASSWORD）",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        shops, shop_created = self._seed_shops()
        dish_created, dish_updated = self._seed_dishes(shops)
        roster_created = self._seed_roster()

        if options["admin"]:
            self._seed_admin()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("演示数据导入完成"))
        self.stdout.write(f"  档口   {Shop.objects.count():>3} 家（本次新增 {shop_created}）")
        self.stdout.write(f"  菜品   {Dish.objects.count():>3} 道（新增 {dish_created}，更新 {dish_updated}）")
        self.stdout.write(f"  学籍   {len(ROSTER)} 条（本次新增 {roster_created}）")
        self.stdout.write("")
        self.stdout.write("试用流程：")
        self.stdout.write("  1) POST /api/auth/register/  注册一个账号")
        self.stdout.write("  2) POST /api/auth/bind-student/  student_id=20230001 name=张同学 college=计算机学院")
        self.stdout.write("  3) GET  /api/dishes/random/?source=canteen")
        self.stdout.write("  4) POST /api/checkins/  →  POST /api/votes/  →  POST /api/votes/1/cast/")

    # -- 内部步骤 ---------------------------------------------------------
    def _reset(self) -> None:
        shop_names = [item["name"] for item in SHOPS]
        dish_names = [item["name"] for item in DISHES]
        Dish.objects.filter(name__in=dish_names).delete()
        Shop.objects.filter(name__in=shop_names).delete()
        # 只删「占位账号」：学号在名单里、且没有可用密码（真人账号不动）
        removed = 0
        for item in ROSTER:
            placeholder = User.objects.filter(
                student_id=item["student_id"], name=item["name"], college=item["college"]
            ).first()
            if placeholder and placeholder.is_roster_placeholder:
                placeholder.delete()
                removed += 1
        self.stdout.write(
            self.style.WARNING(f"已清理演示数据（档口 {len(shop_names)} / 菜品 {len(dish_names)} / 学籍 {removed}）")
        )

    def _seed_shops(self) -> tuple[dict[int, Shop], int]:
        result: dict[int, Shop] = {}
        created_count = 0
        for index, item in enumerate(SHOPS):
            shop, created = Shop.objects.get_or_create(
                name=item["name"],
                defaults={
                    "type": item["type"],
                    "location": item["location"],
                    "status": Shop.Status.OPEN,
                },
            )
            if not created:
                changed_fields = []
                if shop.type != item["type"]:
                    shop.type = item["type"]
                    changed_fields.append("type")
                if shop.location != item["location"]:
                    shop.location = item["location"]
                    changed_fields.append("location")
                if changed_fields:
                    shop.save(update_fields=changed_fields)
            if created:
                created_count += 1
            result[index] = shop
        return result, created_count

    def _seed_dishes(self, shops: dict[int, Shop]) -> tuple[int, int]:
        created = updated = 0
        for item in DISHES:
            shop = shops[item["shop"]]
            dish, is_created = Dish.objects.get_or_create(
                shop=shop,
                name=item["name"],
                defaults={
                    "price": item["price"],
                    "category": item["category"],
                    "description": item["description"],
                    "likes": item["likes"],
                    "favorites": item["favorites"],
                },
            )
            if is_created:
                created += 1
            else:
                updated += 1
        return created, updated

    def _seed_roster(self) -> int:
        created = 0
        for item in ROSTER:
            # 学号已被真人账号占用就跳过，绝不覆盖真实绑定
            if User.objects.filter(student_id=item["student_id"]).exists():
                continue
            user = User(
                username=f"roster_{item['student_id']}",
                student_id=item["student_id"],
                name=item["name"],
                college=item["college"],
                role=User.Role.STUDENT,
                status=User.Status.NORMAL,
                is_active=True,
            )
            user.set_unusable_password()  # 占位账号：不可登录，只作为学籍名单
            user.save()
            created += 1
        return created

    def _seed_admin(self) -> None:
        user, created = User.objects.get_or_create(
            username=DEMO_ADMIN_USERNAME,
            defaults={
                "name": "管理员",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "college": "后勤服务中心",
            },
        )
        if created:
            user.set_password(DEMO_ADMIN_PASSWORD)
            user.save(update_fields=["password"])
            self.stdout.write(
                self.style.WARNING(
                    f"已创建后台账号 {DEMO_ADMIN_USERNAME} / {DEMO_ADMIN_PASSWORD}（上线前请修改密码）"
                )
            )
        else:
            self.stdout.write(f"后台账号 {DEMO_ADMIN_USERNAME} 已存在，未改动密码")
