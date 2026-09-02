"""Crea las bases de datos que usan las pruebas.

Las pruebas necesitan dos bases separadas: `kawsay_test` para la bateria
funcional y `kawsay_migration` para el ciclo upgrade/downgrade, que deja el
esquema vacio y destruiria los datos de la otra.

Existe como script porque una purga de Docker se las lleva junto con el volumen,
y reconstruirlas de memoria cada vez es una perdida de tiempo evitable.
"""

import argparse
import os

import pymysql

#: Coincide con `docker-compose.yml`; no es un secreto, esta en el repositorio.
DEFAULT_ADMIN_DSN = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "change_root_local",
}

TEST_DATABASES = ("kawsay_test", "kawsay_migration")
APP_USER = "pwa_app"


def create(dsn: dict, app_user: str) -> None:
    conexion = pymysql.connect(**dsn)
    try:
        with conexion.cursor() as cursor:
            for nombre in TEST_DATABASES:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS {nombre} "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                cursor.execute(f"GRANT ALL PRIVILEGES ON {nombre}.* TO '{app_user}'@'%'")
                print(f"  {nombre}: lista")
            cursor.execute("FLUSH PRIVILEGES")
        conexion.commit()
    finally:
        conexion.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.getenv("MARIADB_HOST", DEFAULT_ADMIN_DSN["host"]))
    parser.add_argument("--port", type=int, default=int(os.getenv("MARIADB_PORT", "3306")))
    parser.add_argument("--user", default=os.getenv("MARIADB_ROOT_USER", DEFAULT_ADMIN_DSN["user"]))
    parser.add_argument(
        "--password",
        default=os.getenv("MARIADB_ROOT_PASSWORD", DEFAULT_ADMIN_DSN["password"]),
    )
    parser.add_argument("--app-user", default=os.getenv("MARIADB_APP_USER", APP_USER))
    args = parser.parse_args()

    if os.getenv("APP_ENV", "development") != "development":
        raise SystemExit("Las bases de prueba solo se crean con APP_ENV=development")

    print("Creando bases de prueba:")
    create(
        {"host": args.host, "port": args.port, "user": args.user, "password": args.password},
        args.app_user,
    )


if __name__ == "__main__":
    main()
