from django.shortcuts import render, redirect
from django.views import View
from django.db import connection
from django.utils import timezone
from django.contrib import messages
from accounts.utils import get_user_id_from_jwt
import uuid

class MeetingsListView(View):
    def get(self, request):
        user_id = get_user_id_from_jwt(request)
        meetings = []
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT vm.MeetingID, vm.MeetingTitle, vm.MeetingDescription, vm.ScheduledDateTime,
                       vm.MeetingDuration, vm.MeetingLink, ms.StatusName
                FROM VideoMeetings vm
                INNER JOIN MeetingStatuses ms ON vm.MeetingStatusID = ms.MeetingStatusID
                INNER JOIN MeetingParticipants mp ON mp.MeetingID = vm.MeetingID
                WHERE mp.UserID = %s
                ORDER BY vm.ScheduledDateTime DESC
                """,
                [user_id or 0]
            )
            for r in cur.fetchall():
                meetings.append({
                    'id': r[0], 'title': r[1], 'desc': r[2], 'dt': r[3], 'dur': r[4], 'link': r[5], 'status': r[6]
                })
        return render(request, 'meetings/index.html', { 'meetings': meetings })

class MeetingCreateView(View):
    def get(self, request):
        if not get_user_id_from_jwt(request):
            return redirect('login')
        attendee_user_id = request.GET.get('user_id')
        return render(request, 'meetings/create.html', { 'attendee_user_id': attendee_user_id })

    def post(self, request):
        user_id = get_user_id_from_jwt(request)
        if not user_id:
            return redirect('login')
        title = (request.POST.get('title') or '').strip()
        description = (request.POST.get('description') or '').strip() or None
        when_iso = request.POST.get('scheduled')
        duration = int(request.POST.get('duration') or '30')
        attendee_user_id = request.POST.get('attendee_user_id')
        if not title:
            messages.error(request, 'Укажите название встречи')
            return render(request, 'meetings/create.html', { 'title': title, 'description': description, 'duration': duration })
        scheduled = timezone.now()
        try:
            if when_iso:
                scheduled = timezone.datetime.fromisoformat(when_iso)
        except Exception:
            scheduled = timezone.now()
        meeting_link = uuid.uuid4().hex

        application_id = None
        with connection.cursor() as cur:
            # 1) основная цель — заявки таргет-пользователя
            target_user = int(attendee_user_id) if attendee_user_id else user_id
            cur.execute("SELECT ApplicationID FROM Applications WHERE UserID=%s ORDER BY ApplicationDate DESC LIMIT 1", [target_user])
            row = cur.fetchone()
            if row:
                application_id = row[0]
            else:
                # пробуем создать заявку для target_user (если роль позволит триггер)
                cur.execute("SELECT AnimalID FROM Animals ORDER BY AnimalID LIMIT 1")
                arow = cur.fetchone()
                animal_id = arow[0] if arow else None
                if animal_id:
                    try:
                        # Проверяем, есть ли уже заявка со статусом 'Pending' на это животное
                        cur.execute("""
                            SELECT COUNT(*) 
                            FROM Applications a
                            JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                            WHERE a.UserID = %s 
                            AND a.AnimalID = %s 
                            AND ast.StatusName = 'Pending'
                        """, [target_user, animal_id])
                        existing_pending = cur.fetchone()[0]
                        
                        if existing_pending == 0:
                            # Получаем StatusID для 'Pending'
                            cur.execute("SELECT StatusID FROM ApplicationStatuses WHERE StatusName = 'Pending'")
                            pending_status_row = cur.fetchone()
                            pending_status_id = pending_status_row[0] if pending_status_row else None
                            
                            if pending_status_id:
                                cur.execute(
                                    """
                                    INSERT INTO Applications (UserID, AnimalID, StatusID, Reason, Experience, HousingConditions, Comment)
                                    VALUES (%s, %s, %s, %s, NULL, NULL, NULL)
                                    RETURNING ApplicationID
                                    """,
                                    [target_user, animal_id, pending_status_id, 'Встреча для знакомства']
                                )
                                created = cur.fetchone()
                                application_id = int(created[0]) if created and created[0] is not None else None
                            else:
                                raise Exception("StatusID для Pending не найден")
                    except Exception:
                        application_id = None

            # 2) если не получилось — используем заявку создателя
            if not application_id:
                cur.execute("SELECT ApplicationID FROM Applications WHERE UserID=%s ORDER BY ApplicationDate DESC LIMIT 1", [user_id])
                row2 = cur.fetchone()
                if row2:
                    application_id = row2[0]
                else:
                    # пробуем создать для создателя
                    if animal_id is None:
                        cur.execute("SELECT AnimalID FROM Animals ORDER BY AnimalID LIMIT 1")
                        arow2 = cur.fetchone()
                        animal_id = arow2[0] if arow2 else None
                    if animal_id:
                        try:
                            # Проверяем, есть ли уже заявка со статусом 'Pending' на это животное
                            cur.execute("""
                                SELECT COUNT(*) 
                                FROM Applications a
                                JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                                WHERE a.UserID = %s 
                                AND a.AnimalID = %s 
                                AND ast.StatusName = 'Pending'
                            """, [user_id, animal_id])
                            existing_pending = cur.fetchone()[0]
                            
                            if existing_pending == 0:
                                # Получаем StatusID для 'Pending'
                                cur.execute("SELECT StatusID FROM ApplicationStatuses WHERE StatusName = 'Pending'")
                                pending_status_row = cur.fetchone()
                                pending_status_id = pending_status_row[0] if pending_status_row else None
                                
                                if pending_status_id:
                                    cur.execute(
                                        """
                                        INSERT INTO Applications (UserID, AnimalID, StatusID, Reason, Experience, HousingConditions, Comment)
                                        VALUES (%s, %s, %s, %s, NULL, NULL, NULL)
                                        RETURNING ApplicationID
                                        """,
                                        [user_id, animal_id, pending_status_id, 'Встреча для знакомства']
                                    )
                                    created = cur.fetchone()
                                    application_id = int(created[0]) if created and created[0] is not None else None
                                else:
                                    raise Exception("StatusID для Pending не найден")
                        except Exception:
                            application_id = None

            # 3) последний шанс — любая существующая заявка в системе
            if not application_id:
                cur.execute("SELECT ApplicationID FROM Applications ORDER BY ApplicationID DESC LIMIT 1")
                anyrow = cur.fetchone()
                if anyrow:
                    application_id = anyrow[0]
        if not application_id:
            messages.error(request, 'Не удалось создать заявку для встречи. Добавьте хотя бы одну заявку пользователю или себе и повторите.')
            return render(request, 'meetings/create.html')

        with connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO VideoMeetings (ApplicationID, MeetingStatusID, MeetingTitle, MeetingDescription, MeetingLink,
                                           ScheduledDateTime, MeetingDuration, CreatedByUserID)
                VALUES (%s, 1, %s, %s, %s, %s, %s, %s)
                RETURNING MeetingID
                """,
                [application_id, title, description, meeting_link, scheduled, duration, user_id]
            )
            # participants: creator as Host
            try:
                val = cur.fetchone()[0]
                meeting_id = int(val) if val is not None else None
            except Exception:
                meeting_id = None
            if meeting_id is None:
                cur.execute("SELECT MeetingID FROM VideoMeetings WHERE MeetingLink=%s ORDER BY MeetingID DESC LIMIT 1", [meeting_link])
                row_mid = cur.fetchone()
                meeting_id = int(row_mid[0]) if row_mid and row_mid[0] is not None else None
            cur.execute("INSERT INTO MeetingParticipants (MeetingID, UserID, ParticipantRole) VALUES (%s, %s, 'Host')", [meeting_id, user_id])
            # applicant as Attendee (if differs)
            cur.execute("SELECT UserID FROM Applications WHERE ApplicationID=%s", [application_id])
            app_user_row = cur.fetchone()
            if app_user_row:
                app_user_id = int(app_user_row[0])
                if app_user_id != user_id:
                    cur.execute("INSERT INTO MeetingParticipants (MeetingID, UserID, ParticipantRole) VALUES (%s, %s, 'Attendee')", [meeting_id, app_user_id])
                    # notify via message (greeting)
                    text = f"Здравствуйте, мы запланировали для вас видеовстречу в {scheduled.strftime('%d.%m.%Y %H:%M')}"
                    cur.execute(
                        """
                        INSERT INTO Messages (SenderID, ParentMessageID, SubjectMessages, MessageText, SendDate, IsRead, RecipientRole)
                        VALUES (%s, NULL, %s, %s, %s, 0, NULL)
                        """,
                        [user_id, 'Видеовстреча', text, timezone.now()]
                    )
        return redirect(f"/meetings/room/{meeting_link}/")

class MeetingRoomView(View):
    def get(self, request, link):
        user_id = get_user_id_from_jwt(request)
        participants = []
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT u.UserID, (u.LastName || ' ' || u.FirstName) AS FullName, COALESCE(mp.ParticipantRole, 'Attendee')
                FROM VideoMeetings vm
                INNER JOIN MeetingParticipants mp ON mp.MeetingID = vm.MeetingID
                INNER JOIN Users u ON u.UserID = mp.UserID
                WHERE vm.MeetingLink = %s
                ORDER BY CASE WHEN mp.ParticipantRole='Host' THEN 0 ELSE 1 END, u.LastName
                """,
                [link]
            )
            for r in cur.fetchall():
                participants.append({ 'user_id': r[0], 'name': r[1], 'role': r[2] })
        return render(request, 'meetings/room.html', { 'link': link, 'participants': participants, 'me_user_id': user_id })
