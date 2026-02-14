import getpass
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from gkeepapi import gpsoauth

from keep_auth import resolve_device_id


ENV_PATH = Path(__file__).with_name(".env")


def upsert_env_var(env_path: Path, key: str, value: str) -> None:
    line_pattern = re.compile(rf"^\s*(export\s+)?{re.escape(key)}=")
    if env_path.exists():
        lines = env_path.read_text().splitlines(keepends=True)
    else:
        lines = []

    updated = False
    updated_lines = []
    for line in lines:
        if line_pattern.match(line):
            prefix = "export " if line.lstrip().startswith("export ") else ""
            updated_lines.append(f'{prefix}{key}="{value}"\n')
            updated = True
            continue
        updated_lines.append(line)

    if not updated:
        if updated_lines and not updated_lines[-1].endswith("\n"):
            updated_lines[-1] += "\n"
        updated_lines.append(f'export {key}="{value}"\n')

    env_path.write_text("".join(updated_lines))


def generate_master_token(username: str, app_password: str, device_id: str) -> str:
    result = gpsoauth.perform_master_login(username, app_password, device_id)
    token = result.get("Token")
    if not token:
        error = result.get("Error", "unknown-error")
        detail = result.get("ErrorDetail", "")
        raise RuntimeError(f"Google login failed: {error} {detail}".strip())
    return token


def main() -> None:
    load_dotenv()

    username = (os.environ.get("username") or input("Google username/email: ")).strip()
    if not username:
        raise RuntimeError("Username is required.")

    app_password = (os.environ.get("GOOGLE_APP_PASSWORD") or "").strip().replace(" ", "")
    if not app_password:
        app_password = getpass.getpass("Google app password (16 chars): ").strip().replace(
            " ", ""
        )
    if not app_password:
        raise RuntimeError("Google app password is required.")

    device_id = resolve_device_id()
    master_token = generate_master_token(username, app_password, device_id)

    upsert_env_var(ENV_PATH, "username", username)
    upsert_env_var(ENV_PATH, "masterKey", master_token)
    print(f"Updated {ENV_PATH} with a new masterKey for {username}.")
    print("Re-run with: ./.venv/bin/python pullTempNotes.py")


if __name__ == "__main__":
    main()
