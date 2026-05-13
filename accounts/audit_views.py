from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.db import connection
from django.utils import timezone
from datetime import datetime
from animals.mixins import AdminRequiredMixin


class AuditLogListView(AdminRequiredMixin, View):
    """Просмотр аудитлога (только админ)"""
    def get(self, request):
        # Используем raw SQL, так как таблица может иметь другую структуру
        q = request.GET.get('q', '').strip()
        action_filter = request.GET.get('action', '')
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        
        # Пагинация
        try:
            page = int(request.GET.get('page', 1))
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1
        per_page = 10  # Количество записей на странице
        offset = (page - 1) * per_page
        
        debug_info = []
        logs = []
        error_message = None
        def _resolve_audit_table_name():
            with connection.cursor() as c:
                c.execute(
                    """
                    SELECT table_schema
                    FROM information_schema.tables
                    WHERE table_name='auditlogs'
                      AND table_schema IN ('public', 'AnimalShelterDB')
                    ORDER BY CASE WHEN table_schema='public' THEN 0 ELSE 1 END
                    LIMIT 1
                    """
                )
                r = c.fetchone()
                if not r:
                    return ("public", "auditlogs")
                return (r[0], "auditlogs")

        schema_name, table_short = _resolve_audit_table_name()
        table_name = f'"{schema_name}".{table_short}' if schema_name != "public" else table_short
        column_map = {}  # Объявляем заранее
        
        # Сначала получим структуру таблицы, чтобы узнать правильные названия столбцов
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    [schema_name, table_short],
                )
                columns = [row[0] for row in cursor.fetchall()]
                
                # Создаём маппинг ожидаемых названий к реальным
                expected_to_real = {
                    'LogID': None,
                    'UserID': None,
                    'Action': None,
                    'EntityType': None,
                    'EntityID': None,
                    'Description': None,
                    'Timestamp': None,
                    'IPAddress': None,
                }
                
                # Пробуем найти столбцы по похожим названиям (точное совпадение сначала)
                for col in columns:
                    col_upper = col.upper()
                    # AuditID -> LogID
                    if col_upper == 'AUDITID':
                        expected_to_real['LogID'] = col
                    # ChangedBy -> UserID
                    elif col_upper == 'CHANGEDBY':
                        expected_to_real['UserID'] = col
                    # Action
                    elif col_upper == 'ACTION':
                        expected_to_real['Action'] = col
                    # TableName -> EntityType
                    elif col_upper == 'TABLENAME':
                        expected_to_real['EntityType'] = col
                    # RecordID -> EntityID
                    elif col_upper == 'RECORDID':
                        expected_to_real['EntityID'] = col
                    # ChangeDate -> Timestamp
                    elif col_upper == 'CHANGEDATE':
                        expected_to_real['Timestamp'] = col
                    # NewValue/OldValue -> Description (объединим их в SELECT)
                    elif col_upper in ['NEWVALUE', 'OLDVALUE']:
                        if expected_to_real['Description'] is None:
                            expected_to_real['Description'] = 'Combined'  # Флаг для комбинированного описания
                    # IPAddress (может отсутствовать)
                    elif 'IP' in col_upper:
                        expected_to_real['IPAddress'] = col
                
                column_map = expected_to_real
                debug_info.append(f"Table structure: {columns}")
                debug_info.append(f"Column mapping: {column_map}")
        except Exception as e:
            debug_info.append(f"Failed to get table structure: {str(e)}")
        
        # Формируем запрос с правильными названиями столбцов
        log_id_col = column_map.get('LogID') or 'AuditID'
        user_id_col = column_map.get('UserID') or 'ChangedBy'
        action_col = column_map.get('Action') or 'Action'
        entity_type_col = column_map.get('EntityType') or 'TableName'
        entity_id_col = column_map.get('EntityID') or 'RecordID'
        # Для Description используем комбинацию OldValue и NewValue
        description_source = column_map.get('Description')
        if description_source == 'Combined' or description_source is None:
            description_col = "COALESCE(al.OldValue::text, '') || ' -> ' || COALESCE(al.NewValue::text, '')"
        else:
            description_col = f"al.{description_source}"
        timestamp_col = column_map.get('Timestamp') or 'ChangeDate'
        ip_address_col = column_map.get('IPAddress')  # Может быть None
        
        # Обновляем условия WHERE с правильными названиями столбцов
        where_conditions_fixed = []
        params_fixed = []
        
        if q:
            # Для поиска используем реальные столбцы
            where_conditions_fixed.append(f"(al.OldValue LIKE %s OR al.NewValue LIKE %s OR al.{entity_type_col} LIKE %s)")
            params_fixed.extend([f'%{q}%', f'%{q}%', f'%{q}%'])
        
        if action_filter:
            where_conditions_fixed.append(f"{action_col} = %s")
            params_fixed.append(action_filter)
        
        if date_from:
            where_conditions_fixed.append(f"CAST({timestamp_col} AS DATE) >= %s")
            params_fixed.append(date_from)
        
        if date_to:
            where_conditions_fixed.append(f"CAST({timestamp_col} AS DATE) <= %s")
            params_fixed.append(date_to)
        
        where_clause_fixed = " AND ".join(where_conditions_fixed) if where_conditions_fixed else "1=1"
        
        # Сначала получаем общее количество записей для пагинации
        count_query = f"""
            SELECT COUNT(*)
            FROM {table_name} al
            WHERE {where_clause_fixed}
        """
        
        total_count = 0
        try:
            with connection.cursor() as cursor:
                cursor.execute(count_query, params_fixed)
                row = cursor.fetchone()
                total_count = row[0] if row else 0
        except Exception as e:
            debug_info.append(f"Failed to get total count: {str(e)}")
        
        # Основной запрос с пагинацией
        query = f"""
            SELECT 
                al.{log_id_col} AS "LogID",
                al.{user_id_col} AS "UserID",
                al.{action_col} AS "Action",
                al.{entity_type_col} AS "EntityType",
                al.{entity_id_col} AS "EntityID",
                {description_col} AS "Description",
                al.{timestamp_col} AS "Timestamp",
                (u.firstname || ' ' || u.lastname) AS "UserName",
                u.email AS "UserEmail"
            FROM {table_name} al
            LEFT JOIN users u ON CAST(al.{user_id_col} AS INT) = u.userid
            WHERE {where_clause_fixed}
            ORDER BY al.{timestamp_col} DESC
            LIMIT {per_page} OFFSET {offset}
        """
        
        params = params_fixed
        
        try:
            # Пробуем выполнить запрос напрямую
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                columns = [col[0] for col in cursor.description]
                debug_info.append(f"Query executed successfully. Columns: {columns}")
                rows = cursor.fetchall()
                debug_info.append(f"Rows found: {len(rows)}")
                
                for row in rows:
                    log_dict = dict(zip(columns, row))
                    # Преобразуем timestamp в объект datetime, если это строка
                    if 'Timestamp' in log_dict and isinstance(log_dict['Timestamp'], str):
                        try:
                            log_dict['Timestamp'] = datetime.fromisoformat(log_dict['Timestamp'].replace('Z', '+00:00'))
                        except:
                            pass
                    logs.append(log_dict)
                
                if len(logs) == 0:
                    debug_info.append("No logs found. This could mean:")
                    debug_info.append("  1. The table is empty")
                    debug_info.append("  2. The filters are too restrictive")
                    debug_info.append("  3. The table structure doesn't match the query")
                    
                    # Пробуем выполнить простой запрос без фильтров
                    try:
                        simple_query = f"SELECT * FROM {table_name} ORDER BY {timestamp_col} DESC LIMIT 5"
                        cursor.execute(simple_query)
                        simple_rows = cursor.fetchall()
                        debug_info.append(f"Simple query without filters returned {len(simple_rows)} rows")
                    except Exception as simple_e:
                        debug_info.append(f"Simple query failed: {str(simple_e)}")
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            error_message = f'Ошибка при загрузке аудитлога: {str(e)}'
            # Логируем детали в консоль
            print(f"[AUDIT LOG ERROR] {error_detail}")
            print(f"[AUDIT LOG ERROR] Query: {query}")
            print(f"[AUDIT LOG ERROR] Params: {params}")
            
            # Пробуем найти таблицу с другим названием
            try:
                with connection.cursor() as cursor:
                    # Проверяем несколько возможных названий таблиц
                    possible_tables = ['auditlogs', 'auditlog', 'audit', 'logs', 'systemlogs']
                    table_found = False
                    for possible_table in possible_tables:
                        try:
                            cursor.execute(f"SELECT * FROM {possible_table} LIMIT 1")
                            table_name = possible_table
                            table_found = True
                            break
                        except:
                            continue
                    
                    if not table_found:
                        # Пробуем получить список всех таблиц
                        cursor.execute(
                            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                        )
                        all_tables = [row[0] for row in cursor.fetchall()]
                        error_message += f' Доступные таблицы: {", ".join(all_tables[:20])}'
            except:
                pass
        
        if error_message:
            messages.warning(request, error_message)
        
        # Выводим отладочную информацию в консоль
        if debug_info:
            print("[AUDIT LOG DEBUG]")
            for info in debug_info:
                print(f"  {info}")
            print(f"[AUDIT LOG DEBUG] Total logs returned: {len(logs)}")
        
        # Вычисляем данные для пагинации
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        has_previous = page > 1
        has_next = page < total_pages
        
        # Список страниц для отображения
        page_numbers = []
        if total_pages <= 7:
            # Показываем все страницы, если их немного
            page_numbers = list(range(1, total_pages + 1))
        else:
            # Показываем первую, последнюю и несколько вокруг текущей
            if page <= 3:
                page_numbers = list(range(1, 4)) + ['...', total_pages]
            elif page >= total_pages - 2:
                page_numbers = [1, '...'] + list(range(total_pages - 2, total_pages + 1))
            else:
                page_numbers = [1, '...', page - 1, page, page + 1, '...', total_pages]
        
        # Получаем уникальные действия для фильтра
        actions = []
        try:
            with connection.cursor() as cursor:
                # Используем правильное название столбца Action
                action_col = column_map.get('Action', 'Action')
                cursor.execute(f"SELECT DISTINCT {action_col} AS Action FROM {table_name} WHERE {action_col} IS NOT NULL ORDER BY Action")
                actions = [row[0] for row in cursor.fetchall()]
        except Exception as e:
            debug_info.append(f"Failed to get actions: {str(e)}")
        
        return render(request, 'accounts/audit_log.html', {
            'logs': logs,
            'actions': actions,
            'q': q,
            'action_filter': action_filter,
            'date_from': date_from,
            'date_to': date_to,
            'page': page,
            'total_pages': total_pages,
            'total_count': total_count,
            'has_previous': has_previous,
            'has_next': has_next,
            'page_numbers': page_numbers,
        })

