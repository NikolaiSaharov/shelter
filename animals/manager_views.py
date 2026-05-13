from django.shortcuts import render, redirect
from django.views import View
from django.db import connection
from news.mixins import AdminOrManagerRequiredMixin
from datetime import datetime, date


class AnimalCardCatalogView(AdminOrManagerRequiredMixin, View):
    """Картотека животных для менеджера с расширенной информацией"""
    
    def get(self, request):
        search_query = request.GET.get('q', '').strip()
        status_filter = request.GET.get('status', '').strip()
        type_filter = request.GET.get('type', '').strip()
        breed_filter = request.GET.get('breed', '').strip()
        manager_shelter_id = getattr(request, 'manager_shelter_id', None)
        
        with connection.cursor() as cursor:
            # Основной запрос для получения животных с расширенной информацией
            query = """
                SELECT 
                    a.AnimalID,
                    a.AnimalName,
                    a.Age,
                    a.Gender,
                    a.Vaccinated,
                    a.Description,
                    a.ImagePath,
                    a.Height,
                    a.AnimalWeight,
                    a.AdmissionDate,
                    s.StatusName AS Status,
                    s.StatusID,
                    b.BreedName,
                    t.TypeName,
                    ac.CharacterName,
                    ac.Description AS CharacterDescription,
                    sh.ShelterID,
                    sh.ShelterName,
                    -- Количество вакцинаций
                    (SELECT COUNT(*) 
                     FROM AnimalVaccinations av 
                     WHERE av.AnimalID = a.AnimalID) AS VaccinationCount,
                    -- Последняя дата вакцинации
                    (SELECT MAX(vr.VaccinationDate) 
                     FROM AnimalVaccinations av
                     INNER JOIN VaccinationRecords vr ON av.AnimalVaccinationID = vr.AnimalVaccinationID
                     WHERE av.AnimalID = a.AnimalID) AS LastVaccinationDate,
                    -- Количество медицинских записей
                    (SELECT COUNT(*) 
                     FROM AnimalMedicalRecords amr 
                     WHERE amr.AnimalID = a.AnimalID) AS MedicalRecordsCount,
                    -- Количество активных медицинских проблем
                    (SELECT COUNT(*) 
                     FROM AnimalMedicalRecords amr 
                     WHERE amr.AnimalID = a.AnimalID AND amr.Status = 'Active') AS ActiveMedicalIssues,
                    -- Количество записей в расписании ухода
                    (SELECT COUNT(*) 
                     FROM AnimalCareSchedule acs 
                     WHERE acs.AnimalID = a.AnimalID AND acs.IsActive = TRUE) AS CareScheduleCount,
                    -- Количество заявок на усыновление
                    (SELECT COUNT(*) 
                     FROM Applications app 
                     WHERE app.AnimalID = a.AnimalID) AS ApplicationsCount,
                    -- Количество пожертвований
                    (SELECT COUNT(*) 
                     FROM Donations d 
                     WHERE d.AnimalID = a.AnimalID) AS DonationsCount,
                    -- Сумма пожертвований
                    (SELECT COALESCE(SUM(Amount), 0) 
                     FROM Donations d 
                     WHERE d.AnimalID = a.AnimalID) AS TotalDonations
                FROM Animals a
                INNER JOIN AnimalStatuses s ON a.StatusID = s.StatusID
                INNER JOIN Breeds b ON a.BreedID = b.BreedID
                INNER JOIN AnimalTypes t ON b.TypeID = t.TypeID
                LEFT JOIN AnimalCharacters ac ON a.CharacterID = ac.CharacterID
                LEFT JOIN Shelters sh ON a.ShelterID = sh.ShelterID
                WHERE 1=1
            """
            
            params = []

            # Менеджер видит животных только своего приюта
            if getattr(request, 'current_user_role', None) == 'Manager':
                query += " AND a.ShelterID = %s"
                params.append(manager_shelter_id)
            
            if search_query:
                query += " AND (a.AnimalName LIKE %s OR a.Description LIKE %s)"
                search_param = f'%{search_query}%'
                params.extend([search_param, search_param])
            
            if status_filter:
                query += " AND s.StatusID = %s"
                params.append(status_filter)
            
            if type_filter:
                query += " AND t.TypeID = %s"
                params.append(type_filter)
            
            if breed_filter:
                query += " AND b.BreedID = %s"
                params.append(breed_filter)
            
            query += " ORDER BY a.AnimalID DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        # Форматируем данные
        animals = []
        for row in rows:
            # Конвертируем рост из метров в сантиметры для отображения
            height_m = row[7] if row[7] else None
            height_cm = height_m * 100 if height_m else None
            
            animals.append({
                'id': row[0],
                'name': row[1],
                'age': row[2],
                'gender': row[3],
                'vaccinated': row[4],
                'description': row[5],
                'image_path': row[6],
                'height': height_cm,  # Рост в сантиметрах для отображения
                'weight': row[8],
                'admission_date': row[9],
                'status': row[10],
                'status_id': row[11],
                'breed': row[12],
                'type': row[13],
                'character': row[14],
                'character_description': row[15],
                'vaccination_count': row[16] or 0,
                'last_vaccination_date': row[17],
                'medical_records_count': row[18] or 0,
                'active_medical_issues': row[19] or 0,
                'care_schedule_count': row[20] or 0,
                'applications_count': row[21] or 0,
                'donations_count': row[22] or 0,
                'total_donations': float(row[23]) if row[23] else 0.0,
                'shelter_id': row[24],
                'shelter_name': row[25],
            })
        
        # Получаем справочники для фильтров
        with connection.cursor() as cursor:
            cursor.execute("SELECT StatusID, StatusName FROM AnimalStatuses ORDER BY StatusName")
            statuses = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]
            
            cursor.execute("SELECT TypeID, TypeName FROM AnimalTypes ORDER BY TypeName")
            types = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]
            
            cursor.execute("SELECT BreedID, BreedName FROM Breeds ORDER BY BreedName")
            breeds = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]
        
        return render(request, 'animals/manager/card_catalog.html', {
            'animals': animals,
            'statuses': statuses,
            'types': types,
            'breeds': breeds,
            'search_query': search_query,
            'status_filter': status_filter,
            'type_filter': type_filter,
            'breed_filter': breed_filter,
        })


class AnimalCardCatalogAllSheltersView(AdminOrManagerRequiredMixin, View):
    """Просмотр животных по всем приютам (только просмотр для менеджера)"""

    def get(self, request):
        # Только менеджерам нужна эта вкладка
        if getattr(request, 'current_user_role', None) != 'Manager':
            return redirect('animal_card_catalog')

        search_query = request.GET.get('q', '').strip()
        status_filter = request.GET.get('status', '').strip()
        type_filter = request.GET.get('type', '').strip()
        breed_filter = request.GET.get('breed', '').strip()
        shelter_filter = request.GET.get('shelter', '').strip()
        page_number = request.GET.get('page', 1)

        with connection.cursor() as cursor:
            query = """
                SELECT 
                    a.AnimalID,
                    a.AnimalName,
                    a.Age,
                    a.Gender,
                    a.Vaccinated,
                    a.Description,
                    a.ImagePath,
                    a.Height,
                    a.AnimalWeight,
                    a.AdmissionDate,
                    s.StatusName AS Status,
                    s.StatusID,
                    b.BreedName,
                    t.TypeName,
                    ac.CharacterName,
                    ac.Description AS CharacterDescription,
                    sh.ShelterID,
                    sh.ShelterName,
                    (SELECT COUNT(*) FROM AnimalVaccinations av WHERE av.AnimalID = a.AnimalID) AS VaccinationCount,
                    (SELECT MAX(vr.VaccinationDate) 
                     FROM AnimalVaccinations av
                     INNER JOIN VaccinationRecords vr ON av.AnimalVaccinationID = vr.AnimalVaccinationID
                     WHERE av.AnimalID = a.AnimalID) AS LastVaccinationDate,
                    (SELECT COUNT(*) FROM AnimalMedicalRecords amr WHERE amr.AnimalID = a.AnimalID) AS MedicalRecordsCount,
                    (SELECT COUNT(*) FROM AnimalMedicalRecords amr WHERE amr.AnimalID = a.AnimalID AND amr.Status = 'Active') AS ActiveMedicalIssues,
                    (SELECT COUNT(*) FROM AnimalCareSchedule acs WHERE acs.AnimalID = a.AnimalID AND acs.IsActive = TRUE) AS CareScheduleCount,
                    (SELECT COUNT(*) FROM Applications app WHERE app.AnimalID = a.AnimalID) AS ApplicationsCount,
                    (SELECT COUNT(*) FROM Donations d WHERE d.AnimalID = a.AnimalID) AS DonationsCount,
                    (SELECT COALESCE(SUM(Amount), 0) FROM Donations d WHERE d.AnimalID = a.AnimalID) AS TotalDonations
                FROM Animals a
                INNER JOIN AnimalStatuses s ON a.StatusID = s.StatusID
                INNER JOIN Breeds b ON a.BreedID = b.BreedID
                INNER JOIN AnimalTypes t ON b.TypeID = t.TypeID
                LEFT JOIN AnimalCharacters ac ON a.CharacterID = ac.CharacterID
                LEFT JOIN Shelters sh ON a.ShelterID = sh.ShelterID
                WHERE 1=1
            """
            params = []

            if search_query:
                query += " AND (a.AnimalName LIKE %s OR a.Description LIKE %s)"
                search_param = f'%{search_query}%'
                params.extend([search_param, search_param])
            if status_filter:
                query += " AND s.StatusID = %s"
                params.append(status_filter)
            if type_filter:
                query += " AND t.TypeID = %s"
                params.append(type_filter)
            if breed_filter:
                query += " AND b.BreedID = %s"
                params.append(breed_filter)
            if shelter_filter:
                query += " AND sh.ShelterID = %s"
                params.append(shelter_filter)

            query += " ORDER BY a.AnimalID DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()

        animals = []
        for row in rows:
            height_m = row[7] if row[7] else None
            height_cm = height_m * 100 if height_m else None
            animals.append({
                'id': row[0],
                'name': row[1],
                'age': row[2],
                'gender': row[3],
                'vaccinated': row[4],
                'description': row[5],
                'image_path': row[6],
                'height': height_cm,
                'weight': row[8],
                'admission_date': row[9],
                'status': row[10],
                'status_id': row[11],
                'breed': row[12],
                'type': row[13],
                'character': row[14],
                'character_description': row[15],
                'shelter_id': row[16],
                'shelter_name': row[17],
                'vaccination_count': row[18] or 0,
                'last_vaccination_date': row[19],
                'medical_records_count': row[20] or 0,
                'active_medical_issues': row[21] or 0,
                'care_schedule_count': row[22] or 0,
                'applications_count': row[23] or 0,
                'donations_count': row[24] or 0,
                'total_donations': float(row[25]) if row[25] else 0.0,
            })

        with connection.cursor() as cursor:
            cursor.execute("SELECT StatusID, StatusName FROM AnimalStatuses ORDER BY StatusName")
            statuses = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]
            cursor.execute("SELECT TypeID, TypeName FROM AnimalTypes ORDER BY TypeName")
            types = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]
            cursor.execute("SELECT BreedID, BreedName FROM Breeds ORDER BY BreedName")
            breeds = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]
            cursor.execute("SELECT ShelterID, ShelterName FROM Shelters WHERE IsActive = TRUE ORDER BY ShelterName")
            shelters = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]

        from django.core.paginator import Paginator
        paginator = Paginator(animals, 12)
        page_obj = paginator.get_page(page_number)

        return render(request, 'animals/manager/card_catalog.html', {
            'animals': page_obj,  # page_obj итерируемый, как список
            'page_obj': page_obj,
            'statuses': statuses,
            'types': types,
            'breeds': breeds,
            'shelters': shelters,
            'search_query': search_query,
            'status_filter': status_filter,
            'type_filter': type_filter,
            'breed_filter': breed_filter,
            'shelter_filter': shelter_filter,
            'all_shelters_mode': True,
        })


class AnimalCardDetailAllSheltersView(AdminOrManagerRequiredMixin, View):
    """Просмотр карточки животного по всем приютам (только просмотр для менеджера)"""

    def get(self, request, pk):
        if getattr(request, 'current_user_role', None) != 'Manager':
            return redirect('animal_card_detail', pk=pk)

        # Копируем логику из AnimalCardDetailView, но без ограничения по приюту
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    a.AnimalID,
                    a.AnimalName,
                    a.Age,
                    a.Gender,
                    a.Vaccinated,
                    a.Description,
                    a.ImagePath,
                    a.Height,
                    a.AnimalWeight,
                    a.AdmissionDate,
                    s.StatusName AS Status,
                    s.StatusID,
                    b.BreedName,
                    b.BreedID,
                    t.TypeName,
                    t.TypeID,
                    ac.CharacterName,
                    ac.CharacterID,
                    ac.Description AS CharacterDescription,
                    sh.ShelterID,
                    sh.ShelterName
                FROM Animals a
                INNER JOIN AnimalStatuses s ON a.StatusID = s.StatusID
                INNER JOIN Breeds b ON a.BreedID = b.BreedID
                INNER JOIN AnimalTypes t ON b.TypeID = t.TypeID
                LEFT JOIN AnimalCharacters ac ON a.CharacterID = ac.CharacterID
                LEFT JOIN Shelters sh ON a.ShelterID = sh.ShelterID
                WHERE a.AnimalID = %s
            """, [pk])
            row = cursor.fetchone()

            if not row:
                from django.contrib import messages
                messages.error(request, 'Животное не найдено')
                return redirect('animal_card_catalog_all_shelters')

            height_m = row[7] if row[7] else None
            height_cm = height_m * 100 if height_m else None

            animal = {
                'id': row[0],
                'name': row[1],
                'age': row[2],
                'gender': row[3],
                'vaccinated': row[4],
                'description': row[5],
                'image_path': row[6],
                'height': height_cm,
                'weight': row[8],
                'admission_date': row[9],
                'status': row[10],
                'status_id': row[11],
                'breed': row[12],
                'breed_id': row[13],
                'type': row[14],
                'type_id': row[15],
                'character': row[16],
                'character_id': row[17],
                'character_description': row[18],
                'shelter_id': row[19],
                'shelter_name': row[20],
            }

            # Вакцинации
            cursor.execute("""
                SELECT 
                    vt.VaccinationName,
                    vr.VaccinationDate,
                    vt.Description
                FROM AnimalVaccinations av
                INNER JOIN VaccinationTypes vt ON av.VaccinationTypeID = vt.VaccinationTypeID
                LEFT JOIN VaccinationRecords vr ON av.AnimalVaccinationID = vr.AnimalVaccinationID
                WHERE av.AnimalID = %s
                ORDER BY vr.VaccinationDate DESC
            """, [pk])
            vaccinations = [{'name': r[0], 'date': r[1], 'description': r[2]} for r in cursor.fetchall()]

            # Медицинские записи
            cursor.execute("""
                SELECT 
                    Condition,
                    DiagnosisDate,
                    Treatment,
                    Status,
                    Notes
                FROM AnimalMedicalRecords
                WHERE AnimalID = %s
                ORDER BY DiagnosisDate DESC
            """, [pk])
            medical_records = [{
                'condition': r[0],
                'diagnosis_date': r[1],
                'treatment': r[2],
                'status': r[3],
                'notes': r[4]
            } for r in cursor.fetchall()]

            # Расписание ухода
            cursor.execute("""
                SELECT 
                    Activity,
                    Frequency,
                    Time,
                    Description,
                    Notes,
                    IsActive
                FROM AnimalCareSchedule
                WHERE AnimalID = %s
                ORDER BY IsActive DESC
            """, [pk])
            care_schedule = [{
                'activity': r[0],
                'frequency': r[1],
                'time': r[2],
                'description': r[3],
                'notes': r[4],
                'is_active': r[5]
            } for r in cursor.fetchall()]

            # Заявки и пожертвования (как в исходной вьюхе)
            cursor.execute("""
                SELECT 
                    a.ApplicationID,
                    a.ApplicationDate,
                    ast.StatusName,
                    u.FirstName || ' ' || u.LastName AS UserName,
                    u.Email
                FROM Applications a
                JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                JOIN Users u ON a.UserID = u.UserID
                WHERE a.AnimalID = %s
                ORDER BY a.ApplicationDate DESC
            """, [pk])
            applications = [{
                'id': r[0],
                'date': r[1],
                'status': r[2],
                'user_name': r[3],
                'email': r[4],
            } for r in cursor.fetchall()]

            cursor.execute("""
                SELECT 
                    DonationID,
                    DonationDate,
                    Amount,
                    u.FirstName || ' ' || u.LastName AS UserName
                FROM Donations d
                JOIN Users u ON d.UserID = u.UserID
                WHERE d.AnimalID = %s
                ORDER BY DonationDate DESC
            """, [pk])
            donations = [{
                'id': r[0],
                'date': r[1],
                'amount': float(r[2] or 0),
                'user_name': r[3],
            } for r in cursor.fetchall()]

        return render(request, 'animals/manager/card_detail.html', {
            'animal': animal,
            'vaccinations': vaccinations,
            'medical_records': medical_records,
            'care_schedule': care_schedule,
            'applications': applications,
            'donations': donations,
            'all_shelters_mode': True,
        })


class AnimalCardDetailView(AdminOrManagerRequiredMixin, View):
    """Детальная карточка животного для менеджера"""
    
    def get(self, request, pk):
        with connection.cursor() as cursor:
            # Основная информация о животном
            cursor.execute("""
                SELECT 
                    a.AnimalID,
                    a.AnimalName,
                    a.Age,
                    a.Gender,
                    a.Vaccinated,
                    a.Description,
                    a.ImagePath,
                    a.Height,
                    a.AnimalWeight,
                    a.AdmissionDate,
                    s.StatusName AS Status,
                    s.StatusID,
                    b.BreedName,
                    b.BreedID,
                    t.TypeName,
                    t.TypeID,
                    ac.CharacterName,
                    ac.CharacterID,
                    ac.Description AS CharacterDescription,
                    sh.ShelterID,
                    sh.ShelterName
                FROM Animals a
                INNER JOIN AnimalStatuses s ON a.StatusID = s.StatusID
                INNER JOIN Breeds b ON a.BreedID = b.BreedID
                INNER JOIN AnimalTypes t ON b.TypeID = t.TypeID
                LEFT JOIN AnimalCharacters ac ON a.CharacterID = ac.CharacterID
                LEFT JOIN Shelters sh ON a.ShelterID = sh.ShelterID
                WHERE a.AnimalID = %s
            """, [pk])
            
            row = cursor.fetchone()
            
            if not row:
                from django.contrib import messages
                messages.error(request, 'Животное не найдено')
                return redirect('animal_card_catalog')
            
            # Конвертируем рост из метров в сантиметры для отображения
            height_m = row[7] if row[7] else None
            height_cm = height_m * 100 if height_m else None
            
            # Ограничение: менеджер работает только со своим приютом
            if getattr(request, 'current_user_role', None) == 'Manager' and row[19] != request.manager_shelter_id:
                messages.error(request, 'Доступ запрещён: животное относится к другому приюту')
                return redirect('animal_card_catalog')

            animal = {
                'id': row[0],
                'name': row[1],
                'age': row[2],
                'gender': row[3],
                'vaccinated': row[4],
                'description': row[5],
                'image_path': row[6],
                'height': height_cm,  # Рост в сантиметрах для отображения
                'weight': row[8],
                'admission_date': row[9],
                'status': row[10],
                'status_id': row[11],
                'breed': row[12],
                'breed_id': row[13],
                'type': row[14],
                'type_id': row[15],
                'character': row[16],
                'character_id': row[17],
                'character_description': row[18],
                'shelter_id': row[19],
                'shelter_name': row[20],
            }
            
            # Вакцинации
            cursor.execute("""
                SELECT 
                    vt.VaccinationName,
                    vr.VaccinationDate,
                    vt.Description
                FROM AnimalVaccinations av
                INNER JOIN VaccinationTypes vt ON av.VaccinationTypeID = vt.VaccinationTypeID
                LEFT JOIN VaccinationRecords vr ON av.AnimalVaccinationID = vr.AnimalVaccinationID
                WHERE av.AnimalID = %s
                ORDER BY vr.VaccinationDate DESC
            """, [pk])
            vaccinations = [{'name': r[0], 'date': r[1], 'description': r[2]} for r in cursor.fetchall()]
            
            # Медицинские записи
            cursor.execute("""
                SELECT 
                    ConditionName,
                    DiagnosisDate,
                    Treatment,
                    Status,
                    Notes
                FROM AnimalMedicalRecords
                WHERE AnimalID = %s
                ORDER BY DiagnosisDate DESC
            """, [pk])
            medical_records = [{
                'condition': r[0],
                'date': r[1],  # Используем 'date' для единообразия
                'diagnosis_date': r[1],
                'treatment': r[2],
                'status': r[3],
                'notes': r[4],
                'diagnosis': r[0],  # ConditionName как diagnosis
            } for r in cursor.fetchall()]
            
            # Расписание ухода
            cursor.execute("""
                SELECT 
                    at.ActivityName,
                    ft.FrequencyName,
                    acs.ScheduleTime,
                    acs.Notes,
                    acs.IsActive,
                    at.Description
                FROM AnimalCareSchedule acs
                INNER JOIN ActivityTypes at ON acs.ActivityTypeID = at.ActivityTypeID
                INNER JOIN FrequencyTypes ft ON acs.FrequencyID = ft.FrequencyID
                WHERE acs.AnimalID = %s
                ORDER BY acs.IsActive DESC, at.ActivityName
            """, [pk])
            care_schedule = [{
                'activity': r[0],
                'frequency': r[1],
                'time': r[2],
                'notes': r[3],
                'is_active': r[4],
                'description': r[5]
            } for r in cursor.fetchall()]
            
            # Заявки на усыновление
            cursor.execute("""
                SELECT 
                    app.ApplicationID,
                    app.ApplicationDate,
                    ast.StatusName,
                    app.Reason,
                    u.FirstName || ' ' || u.LastName AS UserName,
                    u.Email,
                    u.Phone
                FROM Applications app
                INNER JOIN Users u ON app.UserID = u.UserID
                INNER JOIN ApplicationStatuses ast ON app.StatusID = ast.StatusID
                WHERE app.AnimalID = %s
                ORDER BY app.ApplicationDate DESC
            """, [pk])
            applications = [{
                'id': r[0],
                'date': r[1],
                'status_name': r[2],
                'is_approved': r[2] == 'Approved',  # Для обратной совместимости
                'reason': r[3],
                'user_name': r[4],
                'email': r[5],
                'phone': r[6]
            } for r in cursor.fetchall()]
            
            # Пожертвования
            cursor.execute("""
                SELECT 
                    d.DonationID,
                    d.DonationDate,
                    d.Amount,
                    d.Comment,
                    u.FirstName || ' ' || u.LastName AS UserName
                FROM Donations d
                INNER JOIN Users u ON d.UserID = u.UserID
                WHERE d.AnimalID = %s
                ORDER BY d.DonationDate DESC
            """, [pk])
            donations = [{
                'id': r[0],
                'date': r[1],
                'amount': float(r[2]),
                'comment': r[3],
                'user_name': r[4]
            } for r in cursor.fetchall()]
            
            # Сумма пожертвований
            total_donations = sum(d['amount'] for d in donations)
            
            # Хронология событий животного
            timeline = []
            
            # Дата поступления
            if animal['admission_date']:
                timeline.append({
                    'date': animal['admission_date'],
                    'type': 'admission',
                    'title': 'Поступление в приют',
                    'icon': 'bi-calendar-plus',
                    'color': 'primary',
                })
            
            # Вакцинации
            for vac in vaccinations:
                if vac.get('date'):
                    timeline.append({
                        'date': vac['date'],
                        'type': 'vaccination',
                        'title': f'Вакцинация: {vac["name"]}',
                        'icon': 'bi-shield-check',
                        'color': 'success',
                    })
            
            # Медицинские записи
            for med in medical_records:
                if med.get('date'):
                    # Убеждаемся, что дата корректна (может быть None или пустой)
                    med_date = med.get('date')
                    if med_date:
                        timeline.append({
                            'date': med_date,
                            'type': 'medical',
                            'title': f'Медицинская запись: {med.get("diagnosis", med.get("condition", "Лечение"))}',
                            'icon': 'bi-heart-pulse',
                            'color': 'danger',
                        })
            
            # Заявки на усыновление
            for app in applications:
                timeline.append({
                    'date': app['date'],
                    'type': 'application',
                    'title': f'Заявка на усыновление ({"Одобрена" if app.get("is_approved") else "На рассмотрении"})',
                    'icon': 'bi-file-earmark-text',
                    'color': 'info' if app.get('is_approved') else 'secondary',
                })
            
            # Пожертвования
            for don in donations:
                timeline.append({
                    'date': don['date'],
                    'type': 'donation',
                    'title': f'Пожертвование: {don["amount"]} ₽',
                    'icon': 'bi-cash-coin',
                    'color': 'warning',
                })
            
            # Сортируем по дате (новые первыми)
            # Нормализуем все даты к datetime для сравнения
            dt = datetime
            for item in timeline:
                if item.get('date'):
                    item_date = item['date']
                    # Если это date объект, конвертируем в datetime
                    if isinstance(item_date, date) and not isinstance(item_date, datetime):
                        item['date'] = datetime.combine(item_date, datetime.min.time())
            
            timeline.sort(key=lambda x: x['date'] if x.get('date') and isinstance(x['date'], (date, datetime)) else datetime.min, reverse=True)
            
            # Считаем дни в приюте
            days_in_shelter = None
            if animal['admission_date']:
                today = date.today()
                days_in_shelter = (today - animal['admission_date']).days
        
        return render(request, 'animals/manager/card_detail.html', {
            'animal': animal,
            'vaccinations': vaccinations,
            'medical_records': medical_records,
            'care_schedule': care_schedule,
            'applications': applications,
            'donations': donations,
            'total_donations': total_donations,
            'timeline': timeline,
            'days_in_shelter': days_in_shelter,
        })

