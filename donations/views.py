from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db import connection
from django.core import signing
from django.utils import timezone
from django.http import HttpResponse
from django.core.mail import EmailMessage
from django.conf import settings
from accounts.utils import get_user_id_from_jwt
from rest_framework import viewsets
from .models import Donation
from .serializers import DonationSerializer
import io
import os
import platform

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def _safe_localtime(dt):
    """
    В Postgres поля могут оказаться timestamp without time zone -> psycopg отдаёт naive datetime.
    Django timezone.localtime() требует aware datetime.
    """
    if not dt:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return timezone.localtime(dt)


# DRF viewsets (API)
class DonationViewSet(viewsets.ModelViewSet):
    queryset = Donation.objects.all()
    serializer_class = DonationSerializer


# Web views (existing)
class DonationCreateView(View):
    def get(self, request):
        if not get_user_id_from_jwt(request):
            return redirect('login')
        # Ожидаем animal_id из каталога/детейла
        animal_id = request.GET.get('animal_id')
        if not animal_id:
            messages.error(request, 'Выберите животное в каталоге')
            return redirect('/animals/catalog/')
        animal = None
        with connection.cursor() as cur:
            cur.execute("SELECT AnimalID, AnimalName, ImagePath FROM Animals WHERE AnimalID = %s", [animal_id])
            row = cur.fetchone()
            if row:
                animal = { 'id': row[0], 'name': row[1], 'image': row[2] }
        if not animal:
            messages.error(request, 'Питомец не найден')
            return redirect('/animals/catalog/')
        return render(request, 'donations/create.html', { 'animal': animal })

    def post(self, request):
        user_id = get_user_id_from_jwt(request)
        if not user_id:
            return redirect('login')
        animal_id = request.POST.get('animal_id')
        amount = request.POST.get('amount')
        comment = (request.POST.get('comment') or '').strip()
        if not animal_id or not amount:
            messages.error(request, 'Заполните все обязательные поля')
            return redirect('donation_create')
        try:
            amount_val = float(amount)
            if amount_val <= 0:
                raise ValueError
        except Exception:
            messages.error(request, 'Некорректная сумма')
            return redirect('donation_create')
        
        # Создаем токен для имитации оплаты (не сохраняем в БД пока)
        try:
            payload = {
                'u': int(user_id),
                'a': int(animal_id),
                'amt': amount_val,
                'c': comment,
                'ts': timezone.now().timestamp()
            }
            token = signing.dumps(payload, salt='donation')
            return redirect(f'/donations/pay/?token={token}')
        except Exception:
            messages.error(request, 'Ошибка при создании платежной ссылки')
            return redirect('donation_create')

class DonationPayView(View):
    def get(self, request):
        token = request.GET.get('token')
        if not token:
            # Фолбэк: allow GET /donations/pay/?animal_id=..&amount=..&comment=..
            user_id = get_user_id_from_jwt(request)
            animal_id = request.GET.get('animal_id')
            amount = request.GET.get('amount')
            comment = (request.GET.get('comment') or '').strip()
            if user_id and animal_id and amount:
                try:
                    amount_val = float(amount)
                    if amount_val <= 0:
                        raise ValueError
                    payload = { 'u': int(user_id), 'a': int(animal_id), 'amt': amount_val, 'c': comment, 'ts': timezone.now().timestamp() }
                    token = signing.dumps(payload, salt='donation')
                except Exception:
                    messages.error(request, 'Некорректные параметры оплаты')
                    return redirect('donation_create')
            else:
                return redirect('donation_create')
        try:
            data = signing.loads(token, salt='donation', max_age=60*30)
        except Exception:
            messages.error(request, 'Ссылка на оплату недействительна')
            return redirect('donation_create')
        return render(request, 'donations/pay.html', {'data': data, 'token': token})

class DonationConfirmView(View):
    def get(self, request):
        token = request.GET.get('token')
        if not token:
            return redirect('donation_create')
        try:
            data = signing.loads(token, salt='donation', max_age=60*30)
        except Exception:
            messages.error(request, 'Ссылка истекла или недействительна')
            return redirect('donation_create')
        
        # Проверяем, не было ли уже создано пожертвование (защита от повторной оплаты)
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT DonationID FROM Donations 
                WHERE UserID = %s AND AnimalID = %s AND Amount = %s 
                AND ABS(EXTRACT(EPOCH FROM (%s::timestamp - DonationDate))) < 60
                """,
                [data['u'], data['a'], data['amt'], timezone.now()]
            )
            if cur.fetchone():
                messages.info(request, 'Это пожертвование уже было обработано')
                return redirect('/accounts/profile/?tab=donations')
        
        # Пишем пожертвование в БД (имитация успешной оплаты)
        donation_id = None
        with connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO Donations (UserID, AnimalID, Amount, DonationDate, Comment, IsApproved)
                VALUES (%s, %s, %s, NOW(), %s, TRUE)
                RETURNING DonationID, DonationDate
                """,
                [data['u'], data['a'], data['amt'], data.get('c') or None],
            )
            row = cur.fetchone()
            donation_id = int(row[0]) if row and row[0] is not None else None
            donation_date = row[1] if row and len(row) > 1 else timezone.now()

            # Фолбэк: ищем по самым вероятным полям (избавляемся от проблем точности)
            if not donation_id:
                try:
                    amount_dec = round(float(data['amt']), 2)
                except Exception:
                    amount_dec = data['amt']
                cur.execute(
                    """
                    SELECT DonationID, DonationDate
                    FROM Donations
                    WHERE UserID = %s AND AnimalID = %s
                      AND CAST(Amount AS DECIMAL(10,2)) = CAST(%s AS DECIMAL(10,2))
                    ORDER BY DonationDate DESC, DonationID DESC
                    LIMIT 1
                    """,
                    [data['u'], data['a'], amount_dec],
                )
                fb = cur.fetchone()
                if fb:
                    donation_id = int(fb[0])
                    donation_date = fb[1]
                else:
                    donation_date = timezone.now()
            else:
                cur.execute(
                    "SELECT DonationDate FROM Donations WHERE DonationID = %s",
                    [donation_id],
                )
                donation_date_row = cur.fetchone()
                donation_date = donation_date_row[0] if donation_date_row else timezone.now()

        # Пытаемся отправить чек на почту
        if donation_id and HAS_REPORTLAB:
            donation_obj = Donation.objects.select_related('user', 'animal').filter(pk=donation_id).first()
            if donation_obj and donation_obj.user.email:
                try:
                    print(
                        f"[donations] smtp from={settings.EMAIL_HOST_USER} "
                        f"password_set={bool(getattr(settings, 'EMAIL_HOST_PASSWORD', ''))} "
                        f"password_len={len(getattr(settings, 'EMAIL_HOST_PASSWORD', '') or '')}"
                    )
                    print(f"[donations] sending receipt email to={donation_obj.user.email} donation_id={donation_id}")
                    pdf_bytes = DonationReceiptView()._build_pdf(donation_obj)
                    filename = f"donation_receipt_{donation_obj.donation_id}.pdf"
                    donation_date_local = _safe_localtime(donation_obj.donation_date) or timezone.localtime(timezone.now())
                    donation_date_str = donation_date_local.strftime('%d.%m.%Y %H:%M')
                    payer_name = f"{donation_obj.user.first_name} {donation_obj.user.last_name}".strip() or donation_obj.user.email
                    subject = f"Анималити — квитанция о пожертвовании #{donation_obj.donation_id}"
                    body = (
                        f"Здравствуйте, {payer_name}!\n\n"
                        "Спасибо за ваше пожертвование в приют Анималити.\n\n"
                        f"Номер квитанции: #{donation_obj.donation_id}\n"
                        f"Дата: {donation_date_str}\n"
                        f"Сумма: {donation_obj.amount} ₽\n"
                        f"Питомец: {donation_obj.animal.animal_name} (ID: {donation_obj.animal_id})\n\n"
                        "Квитанция в формате PDF прикреплена к письму.\n\n"
                        "Это автоматическое сообщение. Пожалуйста, не отвечайте на него.\n"
                        "Если у вас возникли вопросы — напишите на info@animality.ru.\n"
                    )
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or settings.EMAIL_HOST_USER
                    email = EmailMessage(
                        subject=subject,
                        body=body,
                        from_email=from_email,
                        to=[donation_obj.user.email],
                    )
                    email.attach(filename, pdf_bytes, 'application/pdf')
                    # Отправляем без fail_silently, чтобы увидеть возможную ошибку в консоли
                    email.send(fail_silently=False)
                except Exception as e:
                    # Не ломаем сценарий при ошибке отправки
                    import logging
                    print(f"[donations] ERROR sending receipt email: {e}")
                    logging.getLogger(__name__).warning(f'Ошибка при отправке чека на почту: {e}')
        else:
            # Для диагностики, почему письмо не пытаемся отправлять
            print(f"[donations] receipt email skipped: donation_id={donation_id} HAS_REPORTLAB={HAS_REPORTLAB}")
        
        # Показываем страницу успеха
        return render(request, 'donations/success.html', {
            'amount': data['amt'],
            'donation_id': donation_id,
            'donation_date': donation_date,
        })


class DonationReceiptView(View):
    """PDF‑квитанция о пожертвовании"""
    def _build_pdf(self, donation):
        # Регистрируем шрифт с поддержкой кириллицы
        font_name = 'Helvetica'
        if platform.system() == 'Windows':
            windows_fonts_path = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
            arial_path = os.path.join(windows_fonts_path, 'arial.ttf')
            try:
                if os.path.exists(arial_path):
                    pdfmetrics.registerFont(TTFont('Arial', arial_path))
                    font_name = 'Arial'
            except Exception:
                pass

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=60,
            bottomMargin=50,
        )

        story = []

        primary_color = colors.HexColor('#F08A24')
        secondary_color = colors.HexColor('#FFF3E5')
        dark_text = colors.HexColor('#2b1d16')
        muted_text = colors.HexColor('#6c757d')
        border_color = colors.HexColor('#e5e0db')

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReceiptTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=22,
            textColor=dark_text,
            alignment=TA_LEFT,
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            'ReceiptSubtitle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            textColor=muted_text,
            alignment=TA_LEFT,
            spaceAfter=14,
        )
        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=9,
            textColor=muted_text,
        )
        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=11,
            textColor=dark_text,
        )
        amount_style = ParagraphStyle(
            'Amount',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=22,
            textColor=primary_color,
            alignment=TA_RIGHT,
        )

        # Верхний блок с "логотипом" и номером квитанции
        donation_date = _safe_localtime(donation.donation_date) or timezone.localtime(timezone.now())
        payer_name = f"{donation.user.first_name} {donation.user.last_name}".strip() or donation.user.email

        header_left = [
            Paragraph('<b>Анималити</b>', ParagraphStyle(
                'Brand',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=14,
                textColor=dark_text,
            )),
            Paragraph('Приют для животных', ParagraphStyle(
                'BrandSub',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=9,
                textColor=muted_text,
            )),
        ]
        header_right = [
            Paragraph('<b>Квитанция о пожертвовании</b>', ParagraphStyle(
                'HeaderTitle',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=11,
                textColor=dark_text,
                alignment=TA_RIGHT,
            )),
            Paragraph(
                f'Чек № {donation.donation_id} от {donation_date.strftime("%d.%m.%Y %H:%M")}',
                ParagraphStyle(
                    'HeaderNum',
                    parent=styles['Normal'],
                    fontName=font_name,
                    fontSize=9,
                    textColor=muted_text,
                    alignment=TA_RIGHT,
                ),
            ),
        ]
        header_table = Table(
            [[header_left, header_right]],
            colWidths=[260, 210],
        )
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), secondary_color),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 16))

        # Заголовок квитанции
        story.append(Paragraph('КВИТАНЦИЯ О БЛАГОТВОРИТЕЛЬНОМ ПОЖЕРТВОВАНИИ', title_style))
        story.append(Paragraph('Документ подтверждает приём благотворительного взноса в пользу приюта Анималити.', subtitle_style))

        # Две колонки с реквизитами
        info_left = [
            Paragraph('<b>Плательщик</b>', label_style),
            Paragraph(payer_name, value_style),
            Spacer(1, 4),
            Paragraph('<b>Электронная почта</b>', label_style),
            Paragraph(donation.user.email, value_style),
        ]
        info_right = [
            Paragraph('<b>Получатель средств</b>', label_style),
            Paragraph('Благотворительный приют «Анималити»', value_style),
            Spacer(1, 4),
            Paragraph('<b>Дата операции</b>', label_style),
            Paragraph(donation_date.strftime('%d.%m.%Y %H:%M'), value_style),
        ]
        info_table = Table(
            [[info_left, info_right]],
            colWidths=[240, 230],
        )
        info_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 16))

        # Назначение платежа
        purpose = f'Благотворительное пожертвование на содержание питомца «{donation.animal.animal_name}» (ID: {donation.animal_id}).'
        purpose_block = Table(
            [
                [Paragraph('<b>Назначение платежа</b>', label_style)],
                [Paragraph(purpose, value_style)],
            ],
            colWidths=[470],
        )
        purpose_block.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(purpose_block)
        story.append(Spacer(1, 18))

        # Сумма
        amount_rub = f'{donation.amount:,.2f}'.replace(',', ' ').replace('.00', '')
        amount_block = Table(
            [[
                Paragraph('Итого к зачислению', label_style),
                Paragraph(f'{amount_rub} ₽', amount_style),
            ]],
            colWidths=[230, 240],
        )
        amount_block.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(amount_block)
        story.append(Spacer(1, 20))

        # Подписи
        footer_data = [
            [
                Paragraph('Ответственный за приём средств', label_style),
                '',
                Paragraph('Плательщик', label_style),
                '',
            ],
            [
                Paragraph('__________________________', value_style),
                '',
                Paragraph('__________________________', value_style),
                '',
            ],
        ]
        footer_table = Table(footer_data, colWidths=[180, 70, 180, 40])
        footer_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(footer_table)
        story.append(Spacer(1, 12))

        # Маленький дисклеймер
        story.append(Paragraph(
            'Квитанция сформирована автоматически и не является фискальным документом. '
            'Все средства используются на нужды приюта и помощь животным.',
            ParagraphStyle(
                'Disclaimer',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=8,
                textColor=muted_text,
                alignment=TA_LEFT,
            ),
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def get(self, request, pk):
        user_id = get_user_id_from_jwt(request)
        if not user_id:
            return redirect('login')
        if not HAS_REPORTLAB:
            return HttpResponse('PDF генерация недоступна (требуется reportlab). Установите: pip install reportlab', status=503)

        donation = get_object_or_404(
            Donation.objects.select_related('user', 'animal'),
            pk=pk
        )
        if donation.user_id != user_id:
            return HttpResponse('Доступ к этому чеку запрещен', status=403)

        pdf_bytes = self._build_pdf(donation)
        filename = f"donation_receipt_{donation.donation_id}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
