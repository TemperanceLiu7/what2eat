import os
import sys
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_dev")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

for u in get_user_model().objects.order_by("id"):
    print(f"{u.username:<20} student_id={u.student_id or '-':<12} status={u.status}")
