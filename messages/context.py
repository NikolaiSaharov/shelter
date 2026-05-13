from django.db import connection
from accounts.models import User
from accounts.utils import get_user_id_from_jwt

def _get_user_role(user_id: int):
    """Получает роль пользователя из базы данных"""
    with connection.cursor() as cur:
        cur.execute("SELECT r.RoleName FROM Users u JOIN Roles r ON u.RoleID=r.RoleID WHERE u.UserID=%s", [user_id])
        row = cur.fetchone()
        return row[0] if row else None

def unread_messages(request):
    user_id = get_user_id_from_jwt(request)
    count = 0
    if user_id:
        try:
            user_id = int(user_id)
            role = _get_user_role(user_id)
            if role:
                with connection.cursor() as cur:
                    if role == 'Admin':
                        cur.execute("""
                            SELECT RoleID FROM Roles WHERE RoleName = 'Manager'
                        """)
                        manager_role_row = cur.fetchone()
                        manager_role_id = manager_role_row[0] if manager_role_row else None
                        
                        if manager_role_id:
                            cur.execute("""
                                SELECT COUNT(DISTINCT COALESCE(m.ParentMessageID, m.MessageID))
                                FROM Messages m
                                JOIN Users u ON u.UserID = m.SenderID
                                LEFT JOIN Roles r ON r.RoleID = u.RoleID
                                WHERE m.IsRead = FALSE
                                  AND m.SenderID != %s
                                  AND (
                                        (r.RoleID = %s)
                                        OR (m.RecipientRole = 'Admin')
                                  )
                            """, [user_id, manager_role_id])
                        else:
                            cur.execute("""
                                SELECT COUNT(DISTINCT COALESCE(m.ParentMessageID, m.MessageID))
                                FROM Messages m
                                WHERE m.IsRead = FALSE
                                  AND m.SenderID != %s
                                  AND m.RecipientRole = 'Admin'
                            """, [user_id])
                    elif role == 'Manager':
                        cur.execute("""
                            SELECT RoleID FROM Roles WHERE RoleName = 'Admin'
                        """)
                        admin_role_row = cur.fetchone()
                        admin_role_id = admin_role_row[0] if admin_role_row else None
                        
                        if admin_role_id:
                            cur.execute("""
                                SELECT COUNT(DISTINCT COALESCE(m.ParentMessageID, m.MessageID))
                                FROM Messages m
                                JOIN Users u ON u.UserID = m.SenderID
                                WHERE m.IsRead = FALSE
                                  AND m.SenderID != %s
                                  AND (
                                        m.RecipientRole = 'Manager'
                                        OR (u.RoleID = %s)
                                  )
                                  AND NOT (m.RecipientRole = 'Admin')
                            """, [user_id, admin_role_id])
                        else:
                            cur.execute("""
                                SELECT COUNT(DISTINCT COALESCE(m.ParentMessageID, m.MessageID))
                                FROM Messages m
                                WHERE m.IsRead = FALSE
                                  AND m.SenderID != %s
                                  AND m.RecipientRole = 'Manager'
                                  AND NOT (m.RecipientRole = 'Admin')
                            """, [user_id])
                    else:
                        cur.execute("""
                            SELECT COUNT(DISTINCT COALESCE(m.ParentMessageID, m.MessageID))
                            FROM Messages m
                            JOIN Users u ON u.UserID = m.SenderID
                            LEFT JOIN Roles r ON r.RoleID = u.RoleID
                            WHERE m.IsRead = FALSE
                              AND m.SenderID != %s
                              AND (
                                    m.RecipientRole IS NULL AND r.RoleName IN ('Admin', 'Manager')
                              )
                        """, [user_id])
                    
                    row = cur.fetchone()
                    count = int(row[0]) if row and row[0] else 0
        except Exception as e:
            count = 0
    return { 'unread_messages': count }
