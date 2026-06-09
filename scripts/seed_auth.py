import json
import secrets
from pathlib import Path

from apps.api.services.auth_service import pwd_context

PROJECT_ROOT = Path(__file__).resolve().parents[1]
users_file = PROJECT_ROOT / "users.json"
admin_password = secrets.token_urlsafe(18)

default_users = {
  "users": [
    {
      "username": "admin",
      "password_hash": pwd_context.hash(admin_password),
      "role": "admin",
      "display_name": "Admin User"
    },
    {
      "username": "viewer",
      "password_hash": "$2b$12$/zEg8nsG8wyuP7DSXYE6w.DJS/VwIYXrC0Vz3ZODT6TuF4nSnqHjK",
      "role": "viewer",
      "display_name": "Demo Viewer"
    }
  ]
}

users_file.write_text(json.dumps(default_users, indent=2), encoding="utf-8")
print(f"Auth user store seeded at: {users_file}")
print(f"Local admin credentials: username=admin, password={admin_password}")
print("Viewer demo credentials: username=viewer, password=viewer123")
