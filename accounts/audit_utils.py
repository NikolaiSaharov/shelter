from __future__ import annotations

import logging

from django.db import connection
from django.utils import timezone


logger = logging.getLogger(__name__)


def _resolve_audit_table(cursor) -> str:
    """
    Возвращает имя audit-таблицы с учётом схемы.
    Поддерживаем два варианта:
    - public.auditlogs (обычно)
    - "AnimalShelterDB".auditlogs (если пользователь выставлял search_path/создавал в своей схеме)
    """
    cursor.execute(
        """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_name = 'auditlogs'
          AND table_schema IN ('public', 'AnimalShelterDB')
        ORDER BY CASE WHEN table_schema='public' THEN 0 ELSE 1 END
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    if not row:
        return "auditlogs"
    schema, table = row
    if schema == "public":
        return "auditlogs"
    return f'"{schema}".{table}'


def log_audit(table_name, record_id, action, changed_by, old_value=None, new_value=None):
    """
    Записывает запись в аудитлог
    
    Args:
        table_name: Название таблицы (например, 'Users', 'Animals', 'News')
        record_id: ID измененной записи (должен быть не None)
        action: Действие ('Create', 'Update', 'Delete')
        changed_by: ID пользователя, который внес изменение
        old_value: Старое значение (опционально)
        new_value: Новое значение (опционально)
    """
    # Проверяем обязательные параметры
    if record_id is None:
        logger.warning(f"Failed to write audit log: record_id is None for table {table_name}")
        return
    
    if changed_by is None:
        logger.warning(f"Failed to write audit log: changed_by is None for table {table_name}")
        return
    
    try:
        record_id_int = int(record_id)
        changed_by_int = int(changed_by)
    except (ValueError, TypeError) as e:
        logger.warning(
            "Failed to write audit log: record_id/changed_by not int. "
            "table=%s record_id=%r changed_by=%r error=%s",
            table_name,
            record_id,
            changed_by,
            e,
        )
        return

    try:
        with connection.cursor() as cursor:
            audit_table = _resolve_audit_table(cursor)
            cursor.execute(
                f"""
                INSERT INTO {audit_table}
                  (tablename, recordid, action, changedby, changedate, oldvalue, newvalue)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    str(table_name) if table_name else "",
                    record_id_int,
                    str(action) if action else "",
                    changed_by_int,
                    timezone.now(),
                    str(old_value) if old_value is not None else None,
                    str(new_value) if new_value is not None else None,
                ],
            )
    except Exception as e:
        logger.exception(
            "Failed to write audit log. table=%s record_id=%r changed_by=%r error=%s",
            table_name,
            record_id,
            changed_by,
            e,
        )

