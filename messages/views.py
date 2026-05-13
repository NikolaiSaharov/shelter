from django.shortcuts import render, redirect
from django.views import View
from django.db import connection
from django.contrib import messages
from django.utils import timezone
from accounts.utils import get_user_id_from_jwt

_parent_col = 'ParentMessageID'
_content_col = 'MessageText'
_date_col = 'SendDate'
_isread_col = 'IsRead'
_sender_col = 'SenderID'
_role_col = 'RecipientRole'
_recipient_shelter_col = 'RecipientShelterID'


def _get_user_role(user_id: int):
    with connection.cursor() as cur:
        cur.execute("SELECT r.RoleName FROM Users u JOIN Roles r ON u.RoleID=r.RoleID WHERE u.UserID=%s", [user_id])
        row = cur.fetchone()
        return row[0] if row else None

def _get_user_shelter_id(user_id: int):
    with connection.cursor() as cur:
        cur.execute("SELECT ShelterID FROM Users WHERE UserID=%s", [user_id])
        row = cur.fetchone()
        return row[0] if row else None

def _get_threads(user_id: int):
    role = _get_user_role(user_id)
    shelter_id = _get_user_shelter_id(user_id) if role == 'Manager' else None
    threads = []
    with connection.cursor() as cur:
        if role == 'Admin':

            cur.execute("""
                SELECT RoleID FROM Roles WHERE RoleName = 'Manager'
            """)
            manager_role_row = cur.fetchone()
            manager_role_id = manager_role_row[0] if manager_role_row else None
            
            cur.execute(
                f"""
                WITH user_threads AS (
                    SELECT DISTINCT COALESCE({ _parent_col }, MessageID) AS RootID
                    FROM Messages
                    WHERE { _sender_col } = %s
                ),
                manager_threads AS (
                    SELECT DISTINCT COALESCE(m.{ _parent_col }, m.MessageID) AS RootID
                    FROM Messages m
                    JOIN Users u ON u.UserID = m.{ _sender_col }
                    WHERE m.{ _parent_col } IS NULL 
                      AND u.RoleID = %s
                )
                SELECT DISTINCT m.MessageID AS RootID,
                       (SELECT { _content_col } FROM Messages WHERE MessageID=m.MessageID OR { _parent_col }=m.MessageID ORDER BY { _date_col } DESC LIMIT 1) AS Snippet,
                       (SELECT MAX({ _date_col }) FROM Messages WHERE MessageID=m.MessageID OR { _parent_col }=m.MessageID) AS LastDate,
                       u.FirstName || ' ' || u.LastName AS RootAuthor,
                       m.{ _role_col }
                FROM Messages m
                JOIN Users u ON u.UserID = m.{ _sender_col }
                WHERE m.{ _parent_col } IS NULL
                  AND (
                        m.MessageID IN (SELECT RootID FROM user_threads)
                        OR (u.RoleID = %s AND m.MessageID IN (SELECT RootID FROM manager_threads))
                        OR (m.{ _role_col } = 'Admin')
                  )
                ORDER BY LastDate DESC
                """,
                [user_id, manager_role_id, manager_role_id]
            )
        elif role == 'Manager':

            cur.execute("""
                SELECT RoleID FROM Roles WHERE RoleName = 'Admin'
            """)
            admin_role_row = cur.fetchone()
            admin_role_id = admin_role_row[0] if admin_role_row else None
            
            cur.execute(
                f"""
                WITH user_threads AS (
                    SELECT DISTINCT COALESCE({ _parent_col }, MessageID) AS RootID
                    FROM Messages
                    WHERE { _sender_col } = %s
                ),
                admin_threads AS (
                    SELECT DISTINCT COALESCE(m.{ _parent_col }, m.MessageID) AS RootID
                    FROM Messages m
                    JOIN Users u ON u.UserID = m.{ _sender_col }
                    WHERE m.{ _parent_col } IS NULL 
                      AND u.RoleID = %s
                )
                SELECT DISTINCT m.MessageID AS RootID,
                       (SELECT { _content_col } FROM Messages WHERE MessageID=m.MessageID OR { _parent_col }=m.MessageID ORDER BY { _date_col } DESC LIMIT 1) AS Snippet,
                       (SELECT MAX({ _date_col }) FROM Messages WHERE MessageID=m.MessageID OR { _parent_col }=m.MessageID) AS LastDate,
                       u.FirstName || ' ' || u.LastName AS RootAuthor,
                       m.{ _role_col }
                FROM Messages m
                JOIN Users u ON u.UserID = m.{ _sender_col }
                WHERE m.{ _parent_col } IS NULL
                  AND (
                        m.MessageID IN (SELECT RootID FROM user_threads)
                        OR (m.{ _role_col } = 'Manager' AND (m.{ _recipient_shelter_col } IS NULL OR m.{ _recipient_shelter_col } = %s))
                        OR (u.RoleID = %s AND m.MessageID IN (SELECT RootID FROM admin_threads))
                  )
                  AND NOT (m.{ _role_col } = 'Admin' AND m.{ _sender_col } != %s)
                ORDER BY LastDate DESC
                """,
                [user_id, admin_role_id, shelter_id, admin_role_id, user_id]
            )
        else:

            cur.execute(
                f"""
                WITH user_threads AS (
                    SELECT DISTINCT COALESCE({ _parent_col }, MessageID) AS RootID
                    FROM Messages
                    WHERE { _sender_col } = %s
                )
                SELECT DISTINCT m.MessageID AS RootID,
                       (SELECT { _content_col } FROM Messages WHERE MessageID=m.MessageID OR { _parent_col }=m.MessageID ORDER BY { _date_col } DESC LIMIT 1) AS Snippet,
                       (SELECT MAX({ _date_col }) FROM Messages WHERE MessageID=m.MessageID OR { _parent_col }=m.MessageID) AS LastDate,
                       u.FirstName || ' ' || u.LastName AS RootAuthor,
                       m.{ _role_col }
                FROM Messages m
                JOIN Users u ON u.UserID = m.{ _sender_col }
                LEFT JOIN Roles r ON r.RoleID = u.RoleID
                WHERE m.{ _parent_col } IS NULL
                  AND (
                        m.MessageID IN (SELECT RootID FROM user_threads)
                        OR (m.{ _role_col } IS NULL AND r.RoleName IN ('Admin', 'Manager'))
                  )
                ORDER BY LastDate DESC
                """,
                [user_id]
            )
        results = cur.fetchall()
        
        manager_role_id = None
        admin_role_id = None
        if role == 'Admin':
            cur.execute("SELECT RoleID FROM Roles WHERE RoleName = 'Manager'")
            manager_role_row = cur.fetchone()
            manager_role_id = manager_role_row[0] if manager_role_row else None
        elif role == 'Manager':
            cur.execute("SELECT RoleID FROM Roles WHERE RoleName = 'Admin'")
            admin_role_row = cur.fetchone()
            admin_role_id = admin_role_row[0] if admin_role_row else None
        
        for r in results:
            root_id = r[0]
            unread_count = 0
            try:
                with connection.cursor() as count_cur:
                    if role == 'Admin' and manager_role_id:
                        count_cur.execute(
                            f"""
                            SELECT COUNT(*)
                            FROM Messages m
                            JOIN Users u ON u.UserID = m.{ _sender_col }
                            LEFT JOIN Roles r ON r.RoleID = u.RoleID
                            WHERE (m.MessageID = %s OR m.{ _parent_col } = %s)
                              AND m.{ _isread_col } = FALSE
                              AND m.{ _sender_col } != %s
                              AND (
                                    (r.RoleID = %s)
                                    OR (m.{ _role_col } = 'Admin')
                              )
                            """,
                            [root_id, root_id, user_id, manager_role_id]
                        )
                    elif role == 'Admin':
                        count_cur.execute(
                            f"""
                            SELECT COUNT(*)
                            FROM Messages m
                            WHERE (m.MessageID = %s OR m.{ _parent_col } = %s)
                              AND m.{ _isread_col } = FALSE
                              AND m.{ _sender_col } != %s
                              AND m.{ _role_col } = 'Admin'
                            """,
                            [root_id, root_id, user_id]
                        )
                    elif role == 'Manager' and admin_role_id:
                        count_cur.execute(
                            f"""
                            SELECT COUNT(*)
                            FROM Messages m
                            JOIN Users u ON u.UserID = m.{ _sender_col }
                            WHERE (m.MessageID = %s OR m.{ _parent_col } = %s)
                              AND m.{ _isread_col } = FALSE
                              AND m.{ _sender_col } != %s
                              AND (
                                    (m.{ _role_col } = 'Manager' AND (m.{ _recipient_shelter_col } IS NULL OR m.{ _recipient_shelter_col } = %s))
                                    OR (u.RoleID = %s)
                              )
                              AND NOT (m.{ _role_col } = 'Admin')
                            """,
                            [root_id, root_id, user_id, shelter_id, admin_role_id]
                        )
                    elif role == 'Manager':
                        count_cur.execute(
                            f"""
                            SELECT COUNT(*)
                            FROM Messages m
                            WHERE (m.MessageID = %s OR m.{ _parent_col } = %s)
                              AND m.{ _isread_col } = FALSE
                              AND m.{ _sender_col } != %s
                              AND m.{ _role_col } = 'Manager'
                              AND (m.{ _recipient_shelter_col } IS NULL OR m.{ _recipient_shelter_col } = %s)
                              AND NOT (m.{ _role_col } = 'Admin')
                            """,
                            [root_id, root_id, user_id, shelter_id]
                        )
                    elif role:
                        count_cur.execute(
                            f"""
                            SELECT COUNT(*)
                            FROM Messages m
                            JOIN Users u ON u.UserID = m.{ _sender_col }
                            LEFT JOIN Roles r ON r.RoleID = u.RoleID
                            WHERE (m.MessageID = %s OR m.{ _parent_col } = %s)
                              AND m.{ _isread_col } = FALSE
                              AND m.{ _sender_col } != %s
                              AND (
                                    m.{ _role_col } IS NULL AND r.RoleName IN ('Admin', 'Manager')
                              )
                            """,
                            [root_id, root_id, user_id]
                        )
                    unread_row = count_cur.fetchone()
                    unread_count = int(unread_row[0]) if unread_row and unread_row[0] else 0
            except Exception:
                unread_count = 0
            
            date_value = r[2]
            # Если дата naive, делаем её aware (предполагаем UTC из SQL Server)
            if date_value and timezone.is_naive(date_value):
                date_value = timezone.make_aware(date_value, timezone.utc)
            
            threads.append({
                'id': root_id,
                'snippet': (r[1] or '')[:160],
                'date': date_value,
                'root_author': r[3],
                'to_role': r[4],
                'unread_count': unread_count,
            })
    return threads


def _get_thread_messages(root_id: int):
    with connection.cursor() as cur:
        cur.execute(
            f"""
            SELECT m.MessageID, m.{ _sender_col }, (u.FirstName || ' ' || u.LastName) as SenderName, r.RoleName,
                   m.{ _content_col }, m.{ _date_col }
            FROM Messages m
            JOIN Users u ON u.UserID = m.{ _sender_col }
            LEFT JOIN Roles r ON r.RoleID = u.RoleID
            WHERE m.MessageID = %s OR m.{ _parent_col } = %s
            ORDER BY m.{ _date_col } ASC
            """,
            [root_id, root_id]
        )
        rows = cur.fetchall()
        try:
            cur.execute(
                f"UPDATE Messages SET { _isread_col }=TRUE WHERE MessageID = %s OR { _parent_col } = %s",
                [root_id, root_id]
            )
        except Exception:
            pass
    from django.utils import timezone as tz
    messages_list = []
    for m in rows:
        date_value = m[5]
        # Если дата naive, делаем её aware (предполагаем UTC из SQL Server)
        if date_value and tz.is_naive(date_value):
            date_value = tz.make_aware(date_value, tz.utc)
        messages_list.append({
            'id': m[0], 
            'sender_id': m[1], 
            'sender_name': m[2], 
            'sender_role': m[3], 
            'content': m[4], 
            'date': date_value
        })
    messages_list.sort(key=lambda x: x['date'] or timezone.now())
    return messages_list

class MessagesListView(View):
    def get(self, request):
        user_id = get_user_id_from_jwt(request)
        if not user_id:
            return redirect('login')
        user_role = _get_user_role(user_id)
        from animals.models import Shelter
        shelters = Shelter.objects.filter(is_active=True).order_by('shelter_name')
        user_shelter_id = _get_user_shelter_id(user_id)
        threads = _get_threads(user_id)
        thread_id = request.GET.get('thread')
        messages_list = None
        counter_user_id = None
        if thread_id and thread_id.isdigit():
            messages_list = _get_thread_messages(int(thread_id))
            for m in messages_list:
                if m['sender_id'] != user_id:
                    counter_user_id = m['sender_id']
                    break
        return render(request, 'messages/index.html', {
            'threads': threads,
            'messages_list': messages_list,
            'root_id': int(thread_id) if thread_id and thread_id.isdigit() else None,
            'counter_user_id': counter_user_id,
            'user_role': user_role,
            'is_admin': user_role == 'Admin',
            'current_user_id': user_id,
            'shelters': shelters,
            'user_shelter_id': user_shelter_id,
        })

class MessageThreadView(View):
    def get(self, request, pk):
        return redirect(f'/messages/?thread={pk}')

    def post(self, request, pk):
        user_id = get_user_id_from_jwt(request)
        if not user_id:
            return redirect('login')
        content = (request.POST.get('content') or '').strip()
        if not content:
            messages.error(request, 'Введите текст сообщения')
            return redirect('messages_home')
        with connection.cursor() as cur:
            cur.execute(
                f"INSERT INTO Messages ({ _sender_col }, { _content_col }, { _date_col }, { _parent_col }, { _isread_col }) VALUES (%s, %s, %s, %s, FALSE)",
                [user_id, content, timezone.now(), pk]
            )
        return redirect(f'/messages/?thread={pk}')

class ComposeMessageView(View):
    def post(self, request):
        user_id = get_user_id_from_jwt(request)
        if not user_id:
            return redirect('login')
        user_role = _get_user_role(user_id)
        subject = (request.POST.get('subject') or '').strip()
        content = (request.POST.get('content') or '').strip()
        role = (request.POST.get('recipient_role') or '').strip() or None
        recipient_shelter_id = (request.POST.get('recipient_shelter_id') or '').strip() or None
        
        if user_role == 'Admin' and role == 'Admin':
            messages.error(request, 'Админ может писать только менеджерам')
            return redirect('messages_home')
        
        if not content:
            messages.error(request, 'Введите текст сообщения')
            return redirect('messages_home')

        # Если пишем менеджерам — обязательно выбираем приют (админам это не нужно)
        if role == 'Manager' and not recipient_shelter_id:
            messages.error(request, 'Выберите приют для отправки менеджерам')
            return redirect('messages_home')
        with connection.cursor() as cur:
            cur.execute(
                f"INSERT INTO Messages ({ _sender_col }, { _parent_col }, SubjectMessages, { _content_col }, { _date_col }, { _isread_col }, { _role_col }, { _recipient_shelter_col }) VALUES (%s, NULL, %s, %s, %s, FALSE, %s, %s) RETURNING MessageID",
                [user_id, subject if subject else None, content, timezone.now(), role, int(recipient_shelter_id) if role == 'Manager' and recipient_shelter_id else None]
            )
            try:
                row = cur.fetchone()
                root_id = row[0] if row and row[0] is not None else None
            except Exception:
                root_id = None
            if root_id is None:
                cur.execute("SELECT MessageID FROM Messages WHERE SenderID=%s AND ParentMessageID IS NULL ORDER BY MessageID DESC LIMIT 1", [user_id])
                row = cur.fetchone()
                root_id = row[0] if row else None
        if not root_id:
            messages.success(request, 'Сообщение отправлено')
            return redirect('messages_home')
        return redirect(f'/messages/?thread={root_id}')

class DeleteMessageView(View):
    def post(self, request, pk):
        user_id = get_user_id_from_jwt(request)
        if not user_id:
            return redirect('login')
        thread = request.GET.get('thread')
        with connection.cursor() as cur:
            cur.execute(f"SELECT MessageID, {_sender_col}, {_parent_col} FROM Messages WHERE MessageID=%s", [pk])
            row = cur.fetchone()
            if not row:
                return redirect('messages_home')
            _, sender_id, parent_id = row
            if sender_id != user_id:
                messages.error(request, 'Можно удалять только свои сообщения')
                return redirect('messages_home')
            if parent_id is None:
                cur.execute(f"DELETE FROM Messages WHERE MessageID=%s OR {_parent_col}=%s", [pk, pk])
                return redirect('messages_home')
            else:
                cur.execute("DELETE FROM Messages WHERE MessageID=%s", [pk])
                if thread and thread.isdigit():
                    return redirect(f'/messages/?thread={thread}')
                return redirect('messages_home')
