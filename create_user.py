#!/usr/bin/env python3
"""Create or reset a dashboard user: python create_user.py <usuario>"""

import getpass
import sys

from src.config import Config
from src.database import DatabasePool
from src.web.auth import ensure_users_table, create_or_update_user


def main():
    if len(sys.argv) != 2:
        print("Uso: python create_user.py <usuario>")
        sys.exit(1)

    username = sys.argv[1].strip()
    Config.validate()
    DatabasePool.initialize()
    ensure_users_table()

    senha = getpass.getpass(f"Senha para {username}: ")
    if len(senha) < 8:
        print("A senha precisa ter pelo menos 8 caracteres.")
        sys.exit(1)
    if senha != getpass.getpass("Repita a senha: "):
        print("The passwords do not match.")
        sys.exit(1)

    email = input("E-mail for the daily report (leave empty to skip): ").strip()

    create_or_update_user(username, senha, email)
    print(f"Usuário '{username}' saved.")


if __name__ == "__main__":
    main()
