from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "今天吃什么"

    def ready(self) -> None:
        # 注册 drf-spectacular 的认证方案扩展（不 import 就不会生效）
        from . import schema  # noqa: F401
