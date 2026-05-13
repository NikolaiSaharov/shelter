from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db import connection, transaction
from django.core.paginator import Paginator
from django.conf import settings
from django.core.mail import send_mail
from news.mixins import AdminOrManagerRequiredMixin
from news.models import News
from accounts.utils import get_user_id_from_jwt


def _send_application_status_email(*, to_email: str | None, subject: str, body: str) -> None:
    if not to_email:
        return
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception:
        # Не ломаем бизнес-процесс из-за проблем с почтой
        import logging
        logging.getLogger(__name__).exception('Failed to send application status email')

class ApplicationsManagerListView(AdminOrManagerRequiredMixin, View):
    """Список всех заявок для менеджера"""
    def get(self, request):
        # Фильтры
        status_filter = request.GET.get('status', '')
        search_query = request.GET.get('q', '').strip()
        manager_shelter_id = getattr(request, 'manager_shelter_id', None)
        
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    a.ApplicationID,
                    a.ApplicationDate,
                    a.StatusID,
                    ast.StatusName,
                    a.Reason,
                    a.Comment,
                    an.AnimalName,
                    u.UserID,
                    u.FirstName || ' ' || u.LastName AS UserName,
                    u.Email,
                    u.Phone
                FROM Applications a
                JOIN Animals an ON a.AnimalID = an.AnimalID
                JOIN Users u ON a.UserID = u.UserID
                JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                WHERE 1=1
            """
            params = []

            # Менеджер видит заявки только своего приюта
            if getattr(request, 'current_user_role', None) == 'Manager':
                query += " AND an.ShelterID = %s"
                params.append(manager_shelter_id)
            
            if status_filter == 'approved':
                query += " AND ast.StatusName = 'Approved'"
            elif status_filter == 'pending':
                query += " AND ast.StatusName = 'Pending'"
            elif status_filter == 'rejected':
                query += " AND ast.StatusName = 'Rejected'"
            
            if search_query:
                query += " AND (an.AnimalName LIKE %s OR u.FirstName || ' ' || u.LastName LIKE %s OR u.Email LIKE %s)"
                search_param = f'%{search_query}%'
                params.extend([search_param, search_param, search_param])
            
            query += " ORDER BY a.ApplicationDate DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        applications = []
        for r in rows:
            app_id, app_date, status_id, status_name, reason, comment, animal_name, user_id, user_name, email, phone = r
            
            # Определяем статус на основе StatusName
            if status_name == 'Approved':
                status = 'Одобрено'
                status_class = 'success'
            elif status_name == 'Rejected':
                status = 'Отклонено'
                status_class = 'danger'
            else:  # Pending
                status = 'В ожидании'
                status_class = 'warning'
            
            applications.append({
                'id': app_id,
                'date': app_date,
                'status': status,
                'status_class': status_class,
                'reason': reason,
                'animal_name': animal_name,
                'user_id': user_id,
                'user_name': user_name,
                'email': email,
                'phone': phone,
            })
        
        # Пагинация - по 12 записей на страницу
        paginator = Paginator(applications, 12)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'accounts/manager/applications_list.html', {
            'page_obj': page_obj,
            'applications': page_obj,  # Для обратной совместимости
            'status_filter': status_filter,
            'search_query': search_query,
        })


class ApplicationManagerDetailView(AdminOrManagerRequiredMixin, View):
    """Детальный просмотр заявки для менеджера"""
    def get(self, request, pk):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    a.ApplicationID,
                    a.ApplicationDate,
                    a.StatusID,
                    ast.StatusName,
                    a.Reason,
                    a.Experience,
                    a.HousingConditions,
                    a.Comment,
                    an.AnimalName,
                    an.AnimalID,
                    an.ShelterID,
                    u.UserID,
                    u.FirstName,
                    u.LastName,
                    u.Email,
                    u.Phone,
                    up.DateOfBirth,
                    up.HomeAddress
                FROM Applications a
                JOIN Animals an ON a.AnimalID = an.AnimalID
                JOIN Users u ON a.UserID = u.UserID
                JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                LEFT JOIN UserProfiles up ON u.UserID = up.UserID
                WHERE a.ApplicationID = %s
            """, [pk])
            
            row = cursor.fetchone()
        
        if not row:
            messages.error(request, 'Заявка не найдена')
            return redirect('applications_manager_list')
        
        app_id, app_date, status_id, status_name, reason, experience, housing, comment, animal_name, animal_id, animal_shelter_id, user_id, first_name, last_name, email, phone, dob, address = row

        # Ограничение: менеджер работает только со своим приютом
        if getattr(request, 'current_user_role', None) == 'Manager' and animal_shelter_id != request.manager_shelter_id:
            messages.error(request, 'Доступ запрещён: заявка относится к другому приюту')
            return redirect('applications_manager_list')
        
        # Определяем статус на основе StatusName
        if status_name == 'Approved':
            status = 'Одобрено'
            status_class = 'success'
            is_approved = True
        elif status_name == 'Rejected':
            status = 'Отклонено'
            status_class = 'danger'
            is_approved = False
        else:  # Pending
            status = 'В ожидании'
            status_class = 'warning'
            is_approved = False
        
        application = {
            'id': app_id,
            'date': app_date,
            'status': status,
            'status_class': status_class,
            'is_approved': is_approved,
            'status_id': status_id,
            'status_name': status_name,
            'reason': reason,
            'experience': experience,
            'housing': housing,
            'comment': comment,
            'animal_name': animal_name,
            'animal_id': animal_id,
            'user_id': user_id,
            'user_name': f"{first_name} {last_name}",
            'email': email,
            'phone': phone,
            'date_of_birth': dob,
            'address': address,
        }
        
        return render(request, 'accounts/manager/application_detail.html', {
            'app': application,
        })


class ApplicationManagerApproveView(AdminOrManagerRequiredMixin, View):
    """Одобрение заявки менеджером"""
    def post(self, request, pk):
        user_id = get_user_id_from_jwt(request)
        
        # Проверяем, что pk и user_id валидны
        if not pk or not user_id:
            messages.error(request, 'Неверные параметры запроса')
            return redirect('applications_manager_list')
        
        try:
            pk_int = int(pk)
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            messages.error(request, 'Неверные параметры запроса')
            return redirect('applications_manager_list')
        
        # Проверяем существование заявки и получаем информацию о животном
        with connection.cursor() as check_cursor:
            check_cursor.execute("""
                SELECT a.ApplicationID, a.UserID, a.AnimalID, a.StatusID, ast.StatusName, a.Comment,
                       an.AnimalName, an.ImagePath, an.ShelterID
                FROM Applications a
                INNER JOIN Animals an ON a.AnimalID = an.AnimalID
                INNER JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                WHERE a.ApplicationID = %s
            """, [pk_int])
            row = check_cursor.fetchone()
            
            if not row:
                messages.error(request, 'Заявка не найдена')
                return redirect('applications_manager_list')
            
            app_user_id = row[1]
            animal_id = row[2]
            current_status_id = row[3]
            current_status_name = row[4]
            comment = row[5]
            animal_name = row[6]
            animal_image = row[7]
            animal_shelter_id = row[8]

            if getattr(request, 'current_user_role', None) == 'Manager' and animal_shelter_id != request.manager_shelter_id:
                messages.error(request, 'Доступ запрещён: заявка относится к другому приюту')
                return redirect('applications_manager_list')
            
            # Проверяем, не отклонена ли заявка
            if current_status_name == 'Rejected':
                messages.error(request, 'Нельзя одобрить отклоненную заявку')
                return redirect('application_manager_detail', pk=pk_int)
        
        # Обновляем статус заявки и статус животного
        with transaction.atomic():
            with connection.cursor() as update_cursor:
                # Получаем StatusID для 'Approved' и 'Adopted'
                update_cursor.execute("""
                    SELECT StatusID FROM ApplicationStatuses WHERE StatusName = 'Approved'
                """)
                approved_status_row = update_cursor.fetchone()
                
                update_cursor.execute("""
                    SELECT StatusID FROM AnimalStatuses WHERE StatusName IN ('Пристроен', 'Adopted')
                """)
                adopted_status_row = update_cursor.fetchone()
                
                if not approved_status_row:
                    messages.error(request, 'Статус "Approved" не найден в базе данных')
                    return redirect('application_manager_detail', pk=pk_int)
                
                if not adopted_status_row:
                    messages.error(request, 'Статус "Adopted" не найден в базе данных')
                    return redirect('application_manager_detail', pk=pk_int)
                
                approved_status_id = approved_status_row[0]
                adopted_status_id = adopted_status_row[0]
                
                # Выполняем UPDATE заявки
                update_cursor.execute("""
                    UPDATE Applications 
                    SET StatusID = %s 
                    WHERE ApplicationID = %s
                """, [approved_status_id, pk_int])
                
                # Обновляем статус животного на "Adopted"
                update_cursor.execute("""
                    UPDATE Animals 
                    SET StatusID = %s
                    WHERE AnimalID = (
                        SELECT AnimalID FROM Applications WHERE ApplicationID = %s
                    )
                """, [adopted_status_id, pk_int])
        
        # Создаём новость о том, что для животного нашли хозяина
        try:
            news_title = f"Новый хозяин для {animal_name}"
            news_content = f"Мы нашли хозяина для \"{animal_name}\""
            News.objects.create(
                user_id=user_id_int,
                title=news_title,
                content=news_content,
                is_published=True,
                image_path=(animal_image[:255] if animal_image else None),
            )
        except Exception as news_err:
            # Не блокируем одобрение заявки, если новость не создалась
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'Не удалось автоматически создать новость при одобрении заявки: {news_err}')

        # Email уведомление пользователю
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT u.Email, u.FirstName, an.AnimalName, sh.ShelterName, sh.Address, sh.Phone, sh.Email
                    FROM Applications a
                    JOIN Users u ON a.UserID = u.UserID
                    JOIN Animals an ON a.AnimalID = an.AnimalID
                    LEFT JOIN Shelters sh ON an.ShelterID = sh.ShelterID
                    WHERE a.ApplicationID = %s
                    """,
                    [pk_int],
                )
                info = cursor.fetchone()
            if info:
                to_email, first_name, animal_name_db, shelter_name, shelter_address, shelter_phone, shelter_email = info
                work_hours = 'Ежедневно: 9:00 - 20:00'
                pickup_lines = []
                if shelter_name:
                    pickup_lines.append(f'Приют: {shelter_name}')
                if shelter_address:
                    pickup_lines.append(f'Адрес: {shelter_address}')
                if shelter_phone:
                    pickup_lines.append(f'Телефон: {shelter_phone}')
                if shelter_email:
                    pickup_lines.append(f'Email: {shelter_email}')
                pickup_lines.append(f'Режим работы: {work_hours}')

                pickup_block = "\n".join(pickup_lines) if pickup_lines else "Свяжитесь с приютом, чтобы договориться о времени."
                subject = f'Анималити: заявка #{pk_int} одобрена'
                body = (
                    f'Здравствуйте{", " + first_name if first_name else ""}!\n\n'
                    f'Поздравляем! Ваша заявка на усыновление животного "{animal_name_db}" была одобрена.\n\n'
                    f'Когда и где можно забрать животное:\n{pickup_block}\n\n'
                    f'Если у вас есть вопросы — ответьте на это письмо или свяжитесь с приютом по контактам выше.\n\n'
                    f'С уважением,\nКоманда Анималити'
                )
                _send_application_status_email(to_email=to_email, subject=subject, body=body)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Failed to prepare approval email')
        
        messages.success(request, 'Заявка одобрена')
        return redirect('application_manager_detail', pk=pk_int)


class ApplicationManagerRejectView(AdminOrManagerRequiredMixin, View):
    """Отклонение заявки менеджером"""
    def post(self, request, pk):
        user_id = get_user_id_from_jwt(request)
        rejection_reason = (request.POST.get('rejection_reason') or '').strip()
        
        # Проверяем, что pk и user_id валидны
        if not pk or not user_id:
            messages.error(request, 'Неверные параметры запроса')
            return redirect('applications_manager_list')
        
        try:
            pk_int = int(pk)
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            messages.error(request, 'Неверные параметры запроса')
            return redirect('applications_manager_list')
        
        # Проверяем существование заявки
        with connection.cursor() as check_cursor:
            check_cursor.execute("""
                SELECT a.ApplicationID, a.UserID, a.AnimalID, a.StatusID, ast.StatusName, an.ShelterID
                FROM Applications a
                JOIN Animals an ON a.AnimalID = an.AnimalID
                JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                WHERE a.ApplicationID = %s
            """, [pk_int])
            row = check_cursor.fetchone()
            
            if not row:
                messages.error(request, 'Заявка не найдена')
                return redirect('applications_manager_list')
            
            app_user_id = row[1]
            animal_id = row[2]
            current_status_id = row[3]
            current_status_name = row[4]
            animal_shelter_id = row[5]

            if getattr(request, 'current_user_role', None) == 'Manager' and animal_shelter_id != request.manager_shelter_id:
                messages.error(request, 'Доступ запрещён: заявка относится к другому приюту')
                return redirect('applications_manager_list')
        
        # Получаем StatusID для 'Rejected'
        with connection.cursor() as status_cursor:
            status_cursor.execute("SELECT StatusID FROM ApplicationStatuses WHERE StatusName = 'Rejected'")
            rejected_status_row = status_cursor.fetchone()
            
            if not rejected_status_row:
                messages.error(request, 'Статус "Rejected" не найден в базе данных')
                return redirect('application_manager_detail', pk=pk_int)
            
            rejected_status_id = rejected_status_row[0]
        
        # Обновляем статус заявки
        marker = 'ОТКЛОНЕНО_'
        with transaction.atomic():
            with connection.cursor() as update_cursor:
                if rejection_reason:
                    # Используем CONCAT для избежания проблем с форматированием
                    like_pattern = '%' + marker + '%'
                    update_cursor.execute("""
                        UPDATE Applications 
                        SET StatusID = %s,
                            Comment = CASE 
                                WHEN Comment IS NOT NULL AND Comment NOT LIKE %s 
                                THEN Comment || E'\n' || %s || 'Причина отклонения: ' || %s
                                WHEN Comment IS NULL OR Comment = ''
                                THEN %s || 'Причина отклонения: ' || %s
                                ELSE Comment || E'\n' || 'Причина отклонения: ' || %s
                            END
                        WHERE ApplicationID = %s
                    """, [rejected_status_id, like_pattern, marker, rejection_reason, marker, rejection_reason, rejection_reason, pk_int])
                else:
                    like_pattern = '%' + marker + '%'
                    update_cursor.execute("""
                        UPDATE Applications 
                        SET StatusID = %s,
                            Comment = CASE 
                                WHEN Comment IS NOT NULL AND Comment NOT LIKE %s
                                THEN Comment || E'\n' || %s
                                WHEN Comment IS NULL OR Comment = ''
                                THEN %s
                                ELSE Comment
                            END
                        WHERE ApplicationID = %s
                    """, [rejected_status_id, like_pattern, marker, marker, pk_int])
            
        messages.success(request, 'Заявка отклонена')

        # Email уведомление пользователю
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT u.Email, u.FirstName, an.AnimalName, sh.ShelterName, sh.Address, sh.Phone, sh.Email
                    FROM Applications a
                    JOIN Users u ON a.UserID = u.UserID
                    JOIN Animals an ON a.AnimalID = an.AnimalID
                    LEFT JOIN Shelters sh ON an.ShelterID = sh.ShelterID
                    WHERE a.ApplicationID = %s
                    """,
                    [pk_int],
                )
                info = cursor.fetchone()
            if info:
                to_email, first_name, animal_name_db, shelter_name, shelter_address, shelter_phone, shelter_email = info
                reason_text = rejection_reason if rejection_reason else 'Причина не указана менеджером.'
                contact_lines = []
                if shelter_name:
                    contact_lines.append(f'Приют: {shelter_name}')
                if shelter_address:
                    contact_lines.append(f'Адрес: {shelter_address}')
                if shelter_phone:
                    contact_lines.append(f'Телефон: {shelter_phone}')
                if shelter_email:
                    contact_lines.append(f'Email: {shelter_email}')
                contacts_block = "\n".join(contact_lines) if contact_lines else "Контакты приюта: недоступны."
                subject = f'Анималити: заявка #{pk_int} отклонена'
                body = (
                    f'Здравствуйте{", " + first_name if first_name else ""}.\n\n'
                    f'К сожалению, ваша заявка на усыновление животного "{animal_name_db}" была отклонена.\n\n'
                    f'Причина отказа:\n{reason_text}\n\n'
                    f'Контакты приюта:\n{contacts_block}\n\n'
                    f'Если вы хотите — вы можете подать заявку на другого питомца в нашем каталоге.\n\n'
                    f'С уважением,\nКоманда Анималити'
                )
                _send_application_status_email(to_email=to_email, subject=subject, body=body)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Failed to prepare rejection email')

        return redirect('application_manager_detail', pk=pk_int)

