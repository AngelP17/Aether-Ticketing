import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
users_file = PROJECT_ROOT / "users.json"

default_users = {
  "users": [
    {
      "username": "admin",
      "password_hash": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
      "role": "admin",
      "display_name": "Admin User"
    }
  ]
}

users_file.write_text(json.dumps(default_users, indent=2), encoding="utf-8")
print(f"Auth user store seeded at: {users_file}")
print("Default credentials: username=admin, password=admin123 (automatically migrates to bcrypt on successful login)")
