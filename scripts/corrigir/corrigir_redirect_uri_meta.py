from pathlib import Path
import os

env_path = Path("backend/.env")
lines = env_path.read_text(encoding="utf-8").splitlines()

redirect = os.environ["CF"].rstrip("/") + "/api/facebook-login/callback"

new_lines = []

for line in lines:
    if not line.strip().startswith("META_REDIRECT_URI="):
        new_lines.append(line)

new_lines.append(f"META_REDIRECT_URI={redirect}")

env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

print("META_REDIRECT_URI atualizado para:")
print(redirect)
