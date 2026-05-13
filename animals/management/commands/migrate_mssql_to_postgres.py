from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


def _require_pyodbc():
    try:
        import pyodbc  # type: ignore
    except Exception as e:  # pragma: no cover
        raise CommandError(
            "Не найден модуль 'pyodbc'. Установите зависимости: pip install -r requirements.txt"
        ) from e
    return pyodbc


@dataclass(frozen=True)
class MssqlConnParams:
    server: str
    database: str
    user: str | None
    password: str | None
    driver: str
    trusted_connection: bool
    encrypt: bool
    trust_server_certificate: bool


def _read_mssql_params() -> MssqlConnParams:
    server = os.environ.get("MSSQL_HOST") or os.environ.get("DB_HOST")
    database = os.environ.get("MSSQL_NAME") or os.environ.get("MSSQL_DB") or os.environ.get("DB_NAME")
    user = os.environ.get("MSSQL_USER") or None
    password = os.environ.get("MSSQL_PASSWORD") or None
    driver = os.environ.get("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")
    trusted = (os.environ.get("MSSQL_TRUSTED_CONNECTION", "") or "").lower() in {"1", "true", "yes", "y"}
    encrypt = (os.environ.get("MSSQL_ENCRYPT", "") or "").lower() in {"1", "true", "yes", "y"}
    trust_cert = (os.environ.get("MSSQL_TRUST_SERVER_CERTIFICATE", "true") or "").lower() in {
        "1",
        "true",
        "yes",
        "y",
    }

    if not server or not database:
        raise CommandError(
            "Не заданы параметры MSSQL. Нужно минимум MSSQL_HOST и MSSQL_DB (или DB_HOST/DB_NAME)."
        )

    return MssqlConnParams(
        server=server,
        database=database,
        user=user,
        password=password,
        driver=driver,
        trusted_connection=trusted or (not user),
        encrypt=encrypt,
        trust_server_certificate=trust_cert,
    )


def _build_mssql_conn_str(p: MssqlConnParams) -> str:
    parts = [
        f"DRIVER={{{p.driver}}}",
        f"SERVER={p.server}",
        f"DATABASE={p.database}",
    ]
    if p.trusted_connection:
        parts.append("Trusted_Connection=yes")
    else:
        if not p.user:
            raise CommandError("Для MSSQL не задан MSSQL_USER (и отключён Trusted_Connection).")
        parts.append(f"UID={p.user}")
        parts.append(f"PWD={p.password or ''}")
    if p.encrypt:
        parts.append("Encrypt=yes")
    if p.trust_server_certificate:
        parts.append("TrustServerCertificate=yes")
    return ";".join(parts)


def _pg_cols_for_table(pg_table: str) -> list[str]:
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            [pg_table],
        )
        return [r[0] for r in cur.fetchall()]


def _mssql_tables(pyodbc, mssql_cur) -> list[str]:
    mssql_cur.execute(
        """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
        """
    )
    return [r[0] for r in mssql_cur.fetchall()]


def _mssql_columns(mssql_cur, table: str) -> list[str]:
    mssql_cur.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
        """,
        [table],
    )
    return [r[0] for r in mssql_cur.fetchall()]


def _chunks(it: Iterable[Any], size: int) -> Iterable[list[tuple[Any, ...]]]:
    """
    psycopg executemany ожидает последовательность (tuple/list) параметров.
    pyodbc возвращает строки как pyodbc.Row, поэтому нормализуем в tuple().
    """
    buf: list[tuple[Any, ...]] = []
    for row in it:
        # pyodbc.Row -> tuple; обычные tuple тоже ок
        buf.append(tuple(row))
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


class Command(BaseCommand):
    help = "Миграция данных из MSSQL (source) в PostgreSQL (target) без пересоздания вручную."

    DJANGO_TABLE_PREFIXES = ("django_", "auth_", "admin_", "sessions_", "contenttypes_")

    def add_arguments(self, parser):
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Перед импортом очистить таблицы в PostgreSQL (TRUNCATE ... CASCADE).",
        )
        parser.add_argument(
            "--batch",
            type=int,
            default=2000,
            help="Размер батча вставки (по умолчанию 2000).",
        )
        parser.add_argument(
            "--only",
            nargs="*",
            default=None,
            help="Импортировать только указанные таблицы (MSSQL имена).",
        )
        parser.add_argument(
            "--skip",
            nargs="*",
            default=None,
            help="Пропустить указанные таблицы (MSSQL имена).",
        )

    def handle(self, *args, **opts):
        pyodbc = _require_pyodbc()
        p = _read_mssql_params()
        conn_str = _build_mssql_conn_str(p)

        self.stdout.write("Подключаюсь к MSSQL…")
        try:
            mssql_conn = pyodbc.connect(conn_str)
        except Exception as e:
            raise CommandError(f"Не удалось подключиться к MSSQL: {e}") from e

        try:
            mssql_cur = mssql_conn.cursor()
            tables = _mssql_tables(pyodbc, mssql_cur)

            only = set(t.lower() for t in (opts["only"] or [])) if opts["only"] else None
            skip = set(t.lower() for t in (opts["skip"] or [])) if opts["skip"] else set()
            # По умолчанию не импортируем системные таблицы Django:
            # они создаются через `manage.py migrate` и содержат свои id/уникальные ограничения.
            if only is None:
                skip.update({pfx for pfx in self.DJANGO_TABLE_PREFIXES})

            tables_filtered: list[str] = []
            for t in tables:
                tl = t.lower()
                if only is not None and tl not in only:
                    continue
                if tl in skip:
                    continue
                if only is None and tl.startswith(self.DJANGO_TABLE_PREFIXES):
                    continue
                tables_filtered.append(t)

            if not tables_filtered:
                raise CommandError("Не найдено таблиц для импорта (проверьте --only/--skip).")

            pg_tables = set()
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema='public' AND table_type='BASE TABLE'
                    """
                )
                pg_tables = {r[0] for r in cur.fetchall()}

            # Очищаем target при необходимости
            if opts["truncate"]:
                self.stdout.write("Очищаю таблицы в PostgreSQL…")
                # TRUNCATE только бизнес-таблиц (которые реально импортируем), чтобы не сломать Django таблицы
                dst_tables_for_import = sorted(
                    {
                        t.lower()
                        for t in tables_filtered
                        if t.lower() in pg_tables and not t.lower().startswith(("django_", "auth_", "admin_", "sessions_", "contenttypes_"))
                    }
                )
                with connection.cursor() as cur, transaction.atomic():
                    try:
                        cur.execute("SET session_replication_role = replica;")
                    except Exception:
                        # может требовать суперпользователя — тогда просто продолжаем
                        pass
                    for t in dst_tables_for_import:
                        cur.execute(f'TRUNCATE TABLE "{t}" CASCADE;')
                    try:
                        cur.execute("SET session_replication_role = DEFAULT;")
                    except Exception:
                        pass

            # Импорт
            batch_size = int(opts["batch"])
            self.stdout.write(f"Импортирую таблиц: {len(tables_filtered)} (batch={batch_size})")

            with connection.cursor() as pg_cur, transaction.atomic():
                try:
                    pg_cur.execute("SET session_replication_role = replica;")
                except Exception:
                    pass

                for src_table in tables_filtered:
                    dst_table = src_table.lower()
                    if dst_table not in pg_tables:
                        self.stdout.write(self.style.WARNING(f"SKIP {src_table}: нет таблицы '{dst_table}' в Postgres"))
                        continue

                    src_cols = _mssql_columns(mssql_cur, src_table)
                    dst_cols = _pg_cols_for_table(dst_table)

                    # match columns by lower-case names
                    dst_cols_set = {c.lower() for c in dst_cols}
                    cols = [c for c in src_cols if c.lower() in dst_cols_set]
                    if not cols:
                        self.stdout.write(self.style.WARNING(f"SKIP {src_table}: нет пересечения колонок"))
                        continue

                    dst_cols_ordered = [c.lower() for c in cols]

                    self.stdout.write(f"- {src_table} -> {dst_table} ({len(dst_cols_ordered)} cols)")

                    # fetch all rows from MSSQL
                    select_sql = f"SELECT {', '.join('[' + c + ']' for c in cols)} FROM [dbo].[{src_table}]"
                    mssql_cur.execute(select_sql)

                    placeholders = ", ".join(["%s"] * len(dst_cols_ordered))
                    col_list = ", ".join(f'"{c}"' for c in dst_cols_ordered)
                    insert_sql = f'INSERT INTO "{dst_table}" ({col_list}) VALUES ({placeholders})'

                    total = 0
                    # pyodbc cursor is iterable and streams rows; don't fetchall() to avoid OOM
                    for chunk in _chunks(mssql_cur, batch_size):
                        pg_cur.executemany(insert_sql, chunk)
                        total += len(chunk)

                    self.stdout.write(self.style.SUCCESS(f"  inserted: {total}"))

                # восстановить checks/constraints
                try:
                    pg_cur.execute("SET session_replication_role = DEFAULT;")
                except Exception:
                    pass

            self.stdout.write(self.style.SUCCESS("Готово. Данные перенесены в PostgreSQL."))
            # После импорта синхронизируем sequence/identity, иначе возможны дубли по первичным ключам
            try:
                from django.core.management import call_command

                call_command("sync_postgres_sequences", verbosity=1)
            except Exception:
                self.stdout.write(
                    self.style.WARNING(
                        "Импорт завершён, но синхронизация sequence не выполнилась. Запустите вручную: "
                        "python manage.py sync_postgres_sequences"
                    )
                )
        finally:
            try:
                mssql_conn.close()
            except Exception:
                pass
