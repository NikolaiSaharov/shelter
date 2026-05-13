from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Синхронизирует sequence/identity в PostgreSQL (setval до MAX(id)) после импорта данных."

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            self.stdout.write("Текущая БД не PostgreSQL — пропускаю.")
            return

        with connection.cursor() as cur, transaction.atomic():
            # serial/identity колонки: либо is_identity='YES', либо default nextval('...')::regclass
            cur.execute(
                """
                SELECT
                    c.table_name,
                    c.column_name
                FROM information_schema.columns c
                JOIN information_schema.tables t
                  ON t.table_schema = c.table_schema AND t.table_name = c.table_name
                WHERE c.table_schema = 'public'
                  AND t.table_type = 'BASE TABLE'
                  AND (
                        c.is_identity = 'YES'
                        OR c.column_default LIKE 'nextval(%'
                  )
                ORDER BY c.table_name, c.ordinal_position
                """
            )
            pairs = cur.fetchall()

            updated = 0
            for table_name, column_name in pairs:
                # pg_get_serial_sequence works for both serial and identity-backed sequences in most cases.
                cur.execute("SELECT pg_get_serial_sequence(%s, %s)", [table_name, column_name])
                seq_row = cur.fetchone()
                seq_name = seq_row[0] if seq_row else None
                if not seq_name:
                    continue

                cur.execute(f'SELECT COALESCE(MAX("{column_name}"), 0) FROM "{table_name}"')
                max_id = int(cur.fetchone()[0] or 0)

                # Если таблица пустая, setval(..., 0, true) может быть вне диапазона (обычно sequence стартует с 1).
                # Для пустой таблицы ставим 1 и is_called=false, чтобы следующий nextval вернул 1.
                if max_id <= 0:
                    cur.execute("SELECT setval(%s, %s, false)", [seq_name, 1])
                else:
                    # setval(seq, max, true) => next nextval will be max+1
                    cur.execute("SELECT setval(%s, %s, true)", [seq_name, max_id])
                updated += 1

            self.stdout.write(self.style.SUCCESS(f"Готово. Синхронизировано sequence: {updated}"))

