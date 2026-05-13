from urllib.parse import urlencode

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.db import connection
from django.core import signing
from news.mixins import AdminOrManagerRequiredMixin
from accounts.models import User
from datetime import datetime, date, timedelta, timezone as dt_timezone
from calendar import monthrange


CALENDAR_ICS_SALT = 'animality-vaccination-calendar'
# Блок со ссылкой на Google Calendar на странице /animals/calendar/ (включите True, чтобы снова показать)
SHOW_CALENDAR_GOOGLE_BLOCK = False


def make_calendar_feed_token(user_id: int) -> str:
    return signing.dumps({'uid': user_id}, salt=CALENDAR_ICS_SALT)


def parse_calendar_feed_token(token: str):
    try:
        return signing.loads(token, salt=CALENDAR_ICS_SALT)
    except signing.BadSignature:
        return None


def _ical_escape(text: str) -> str:
    if text is None:
        return ''
    s = str(text).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')
    return s.replace('\r', '')


def _ical_fold_line(line: str) -> str:
    """RFC 5545: fold long lines (octets); упрощённо по символам для ASCII/кириллицы."""
    if len(line) <= 75:
        return line
    parts = []
    pos = 0
    first = True
    while pos < len(line):
        limit = 75 if first else 74
        chunk = line[pos : pos + limit]
        parts.append(('' if first else ' ') + chunk)
        pos += limit
        first = False
    return '\r\n'.join(parts)


def _build_ics_calendar(events, cal_name: str) -> str:
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Анималити//Vaccination Calendar//RU',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        _ical_fold_line(f'X-WR-CALNAME:{_ical_escape(cal_name)}'),
    ]
    now = datetime.now(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    for ev in events:
        d = ev['day']
        if hasattr(d, 'date'):
            d = d.date()
        day_str = d.strftime('%Y%m%d')
        # Весь день: DTEND — следующий день (исключительно)
        end_d = d + timedelta(days=1)
        end_str = end_d.strftime('%Y%m%d')
        uid = ev['uid']
        summary = _ical_escape(ev['summary'])
        desc = _ical_escape(ev.get('description') or '')
        lines.extend(
            [
                'BEGIN:VEVENT',
                f'UID:{uid}',
                f'DTSTAMP:{now}',
                f'DTSTART;VALUE=DATE:{day_str}',
                f'DTEND;VALUE=DATE:{end_str}',
                _ical_fold_line(f'SUMMARY:{summary}'),
            ]
        )
        if desc:
            lines.append(_ical_fold_line(f'DESCRIPTION:{desc}'))
        lines.append('END:VEVENT')
    lines.append('END:VCALENDAR')
    return '\r\n'.join(lines) + '\r\n'


def _shelter_clause_for_manager(request):
    role = getattr(request, 'current_user_role', None)
    sid = getattr(request, 'manager_shelter_id', None)
    if role == 'Manager' and sid:
        return ' AND a.ShelterID = %s', [sid]
    return '', []


class VaccinationCalendarView(AdminOrManagerRequiredMixin, View):
    """Календарь прививок и медицинских процедур"""

    def get(self, request):
        year = request.GET.get('year')
        month = request.GET.get('month')

        today = date.today()
        if year:
            try:
                year = int(year)
            except ValueError:
                year = today.year
        else:
            year = today.year

        if month:
            try:
                month = int(month)
                if month < 1 or month > 12:
                    month = today.month
            except ValueError:
                month = today.month
        else:
            month = today.month

        extra_sql, extra_params = _shelter_clause_for_manager(request)

        with connection.cursor() as cursor:
            start_date = date(year, month, 1)
            days_in_month = monthrange(year, month)[1]
            end_date = date(year, month, days_in_month)

            cursor.execute(
                f"""
                SELECT
                    vr.VaccinationDate,
                    a.AnimalName,
                    vt.VaccinationName,
                    a.AnimalID
                FROM VaccinationRecords vr
                INNER JOIN AnimalVaccinations av ON vr.AnimalVaccinationID = av.AnimalVaccinationID
                INNER JOIN Animals a ON av.AnimalID = a.AnimalID
                INNER JOIN VaccinationTypes vt ON av.VaccinationTypeID = vt.VaccinationTypeID
                WHERE CAST(vr.VaccinationDate AS DATE) BETWEEN %s AND %s
                {extra_sql}
                ORDER BY vr.VaccinationDate
                """,
                [start_date, end_date, *extra_params],
            )

            vaccinations = []
            for row in cursor.fetchall():
                vaccinations.append(
                    {
                        'date': row[0],
                        'animal_name': row[1],
                        'vaccination_name': row[2],
                        'animal_id': row[3],
                        'type': 'vaccination',
                    }
                )

            cursor.execute(
                f"""
                SELECT
                    amr.DiagnosisDate,
                    a.AnimalName,
                    amr.ConditionName,
                    amr.RecordID,
                    a.AnimalID
                FROM AnimalMedicalRecords amr
                INNER JOIN Animals a ON amr.AnimalID = a.AnimalID
                WHERE CAST(amr.DiagnosisDate AS DATE) BETWEEN %s AND %s
                {extra_sql}
                ORDER BY amr.DiagnosisDate
                """,
                [start_date, end_date, *extra_params],
            )

            medical_records = []
            for row in cursor.fetchall():
                medical_records.append(
                    {
                        'date': row[0],
                        'animal_name': row[1],
                        'diagnosis': row[2] or 'Медицинская процедура',
                        'record_id': row[3],
                        'animal_id': row[4],
                        'type': 'medical',
                    }
                )

            all_events = vaccinations + medical_records

            events_by_date = {}
            for event in all_events:
                event_date = event['date'].date() if hasattr(event['date'], 'date') else event['date']
                if event_date not in events_by_date:
                    events_by_date[event_date] = []
                events_by_date[event_date].append(event)

        days_in_month = monthrange(year, month)[1]
        first_day = date(year, month, 1)
        first_weekday = first_day.weekday()

        weeks = []
        week = []

        for _ in range(first_weekday):
            week.append({'day': None, 'events': []})

        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)
            day_events = events_by_date.get(current_date, [])
            week.append(
                {
                    'day': day,
                    'date': current_date,
                    'events': day_events,
                    'is_today': current_date == today,
                }
            )

            if len(week) == 7:
                weeks.append(week)
                week = []

        while len(week) < 7:
            week.append({'day': None, 'events': []})

        if week:
            weeks.append(week)

        if month == 1:
            prev_month = 12
            prev_year = year - 1
        else:
            prev_month = month - 1
            prev_year = year

        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year

        month_names = {
            1: 'Январь',
            2: 'Февраль',
            3: 'Март',
            4: 'Апрель',
            5: 'Май',
            6: 'Июнь',
            7: 'Июль',
            8: 'Август',
            9: 'Сентябрь',
            10: 'Октябрь',
            11: 'Ноябрь',
            12: 'Декабрь',
        }

        total_vaccinations = len(vaccinations)
        total_medical = len(medical_records)

        user = getattr(request, 'current_user', None)
        calendar_feed_url = None
        if SHOW_CALENDAR_GOOGLE_BLOCK and user:
            token = make_calendar_feed_token(user.user_id)
            calendar_feed_url = request.build_absolute_uri(
                reverse('vaccination_calendar_ics') + '?' + urlencode({'t': token})
            )

        return render(
            request,
            'animals/calendar.html',
            {
                'weeks': weeks,
                'year': year,
                'month': month,
                'month_name': month_names[month],
                'prev_year': prev_year,
                'prev_month': prev_month,
                'next_year': next_year,
                'next_month': next_month,
                'today': today,
                'total_vaccinations': total_vaccinations,
                'total_medical': total_medical,
                'calendar_feed_url': calendar_feed_url,
            },
        )


class VaccinationCalendarIcsView(View):
    """
    Подписка Google Calendar / других клиентов по URL (формат iCalendar).
    Доступ по подписанному параметру t=… (без cookie — так работает подписка).
    """

    def get(self, request):
        raw = request.GET.get('t', '')
        payload = parse_calendar_feed_token(raw)
        if not payload or 'uid' not in payload:
            return HttpResponse('Недействительная ссылка', status=403, content_type='text/plain; charset=utf-8')

        try:
            user = User.objects.select_related('role', 'shelter').get(pk=payload['uid'])
        except User.DoesNotExist:
            return HttpResponse('Пользователь не найден', status=403, content_type='text/plain; charset=utf-8')

        role = user.role.role_name if user.role else None
        if role not in ('Admin', 'Manager'):
            return HttpResponse('Доступ запрещён', status=403, content_type='text/plain; charset=utf-8')
        if role == 'Manager' and not user.shelter_id:
            return HttpResponse('Менеджер не привязан к приюту', status=403, content_type='text/plain; charset=utf-8')

        today = date.today()
        start_date = today - timedelta(days=365)
        end_date = today + timedelta(days=730)

        extra_sql = ''
        extra_params: list = []
        if role == 'Manager':
            extra_sql = ' AND a.ShelterID = %s'
            extra_params = [user.shelter_id]

        events = []

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    vr.RecordID,
                    vr.VaccinationDate,
                    a.AnimalName,
                    vt.VaccinationName,
                    a.AnimalID
                FROM VaccinationRecords vr
                INNER JOIN AnimalVaccinations av ON vr.AnimalVaccinationID = av.AnimalVaccinationID
                INNER JOIN Animals a ON av.AnimalID = a.AnimalID
                INNER JOIN VaccinationTypes vt ON av.VaccinationTypeID = vt.VaccinationTypeID
                WHERE CAST(vr.VaccinationDate AS DATE) BETWEEN %s AND %s
                {extra_sql}
                ORDER BY vr.VaccinationDate
                """,
                [start_date, end_date, *extra_params],
            )
            for row in cursor.fetchall():
                rid, vdate, aname, vname, aid = row
                d = vdate.date() if hasattr(vdate, 'date') else vdate
                events.append(
                    {
                        'uid': f'animality-vac-{rid}@animality',
                        'day': d,
                        'summary': f'Прививка: {aname} — {vname}',
                        'description': f'Животное ID {aid}. Вакцинация: {vname}.',
                    }
                )

            cursor.execute(
                f"""
                SELECT
                    amr.RecordID,
                    amr.DiagnosisDate,
                    a.AnimalName,
                    amr.ConditionName,
                    a.AnimalID
                FROM AnimalMedicalRecords amr
                INNER JOIN Animals a ON amr.AnimalID = a.AnimalID
                WHERE CAST(amr.DiagnosisDate AS DATE) BETWEEN %s AND %s
                {extra_sql}
                ORDER BY amr.DiagnosisDate
                """,
                [start_date, end_date, *extra_params],
            )
            for row in cursor.fetchall():
                rid, ddate, aname, cond, aid = row
                d = ddate.date() if hasattr(ddate, 'date') else ddate
                cond = cond or 'Медицинская процедура'
                events.append(
                    {
                        'uid': f'animality-med-{rid}@animality',
                        'day': d,
                        'summary': f'Медицина: {aname} — {cond}',
                        'description': f'Животное ID {aid}. {cond}',
                    }
                )

        if role == 'Manager' and user.shelter:
            cal_name = f'Анималити — {user.shelter.shelter_name}'
        else:
            cal_name = 'Анималити — прививки и процедуры'

        body = _build_ics_calendar(events, cal_name)
        resp = HttpResponse(body, content_type='text/calendar; charset=utf-8')
        resp['Cache-Control'] = 'private, max-age=300'
        return resp
