from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.db import connection
from news.mixins import AdminOrManagerRequiredMixin


class VaccinationsListView(AdminOrManagerRequiredMixin, View):
    """Список вакцинаций для админа/менеджера"""
    
    def get(self, request):
        animal_id = request.GET.get('animal_id', '').strip()
        search_query = request.GET.get('q', '').strip()
        manager_shelter_id = getattr(request, 'manager_shelter_id', None)
        
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    av.AnimalVaccinationID,
                    a.AnimalID,
                    a.AnimalName,
                    vt.VaccinationTypeID,
                    vt.VaccinationName,
                    vt.Description,
                    MAX(vr.VaccinationDate) AS LastVaccinationDate,
                    COUNT(vr.RecordID) AS VaccinationCount
                FROM AnimalVaccinations av
                INNER JOIN Animals a ON av.AnimalID = a.AnimalID
                INNER JOIN VaccinationTypes vt ON av.VaccinationTypeID = vt.VaccinationTypeID
                LEFT JOIN VaccinationRecords vr ON av.AnimalVaccinationID = vr.AnimalVaccinationID
                WHERE 1=1
            """
            
            params = []

            if getattr(request, 'current_user_role', None) == 'Manager':
                query += " AND a.ShelterID = %s"
                params.append(manager_shelter_id)
            
            if animal_id:
                query += " AND a.AnimalID = %s"
                params.append(animal_id)
            
            if search_query:
                query += " AND (vt.VaccinationName LIKE %s OR a.AnimalName LIKE %s)"
                search_param = f'%{search_query}%'
                params.extend([search_param, search_param])
            
            query += """
                GROUP BY 
                    av.AnimalVaccinationID,
                    a.AnimalID,
                    a.AnimalName,
                    vt.VaccinationTypeID,
                    vt.VaccinationName,
                    vt.Description
                ORDER BY a.AnimalName, vt.VaccinationName
            """
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        vaccinations = []
        for row in rows:
            vaccinations.append({
                'id': row[0],
                'animal_id': row[1],
                'animal_name': row[2],
                'vaccination_type_id': row[3],
                'vaccination_name': row[4],
                'description': row[5],
                'last_date': row[6],
                'count': row[7] or 0,
            })
        
        # Список животных для фильтра
        with connection.cursor() as cursor:
            if getattr(request, 'current_user_role', None) == 'Manager':
                cursor.execute("SELECT AnimalID, AnimalName FROM Animals WHERE ShelterID = %s ORDER BY AnimalName", [manager_shelter_id])
            else:
                cursor.execute("SELECT AnimalID, AnimalName FROM Animals ORDER BY AnimalName")
            animals = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]
        
        return render(request, 'animals/vaccination/list.html', {
            'vaccinations': vaccinations,
            'animals': animals,
            'animal_id': animal_id,
            'search_query': search_query,
        })


class VaccinationDetailView(AdminOrManagerRequiredMixin, View):
    """Детальный просмотр вакцинации с историей"""
    
    def get(self, request, pk):
        with connection.cursor() as cursor:
            # Информация о вакцинации
            cursor.execute("""
                SELECT 
                    av.AnimalVaccinationID,
                    a.AnimalID,
                    a.AnimalName,
                    a.ShelterID,
                    vt.VaccinationTypeID,
                    vt.VaccinationName,
                    vt.Description
                FROM AnimalVaccinations av
                INNER JOIN Animals a ON av.AnimalID = a.AnimalID
                INNER JOIN VaccinationTypes vt ON av.VaccinationTypeID = vt.VaccinationTypeID
                WHERE av.AnimalVaccinationID = %s
            """, [pk])
            
            row = cursor.fetchone()
            
            if not row:
                messages.error(request, 'Вакцинация не найдена')
                return redirect('vaccinations_list')
            
            if getattr(request, 'current_user_role', None) == 'Manager' and row[3] != request.manager_shelter_id:
                messages.error(request, 'Доступ запрещён: животное относится к другому приюту')
                return redirect('vaccinations_list')

            vaccination = {
                'id': row[0],
                'animal_id': row[1],
                'animal_name': row[2],
                'type_id': row[4],
                'type_name': row[5],
                'description': row[6],
            }
            
            # История вакцинаций
            cursor.execute("""
                SELECT 
                    RecordID,
                    VaccinationDate
                FROM VaccinationRecords
                WHERE AnimalVaccinationID = %s
                ORDER BY VaccinationDate DESC
            """, [pk])
            
            records = [{'id': r[0], 'date': r[1]} for r in cursor.fetchall()]
        
        return render(request, 'animals/vaccination/detail.html', {
            'vaccination': vaccination,
            'records': records,
        })


class VaccinationCreateView(AdminOrManagerRequiredMixin, View):
    """Создание новой вакцинации"""
    
    def get(self, request):
        animal_id = request.GET.get('animal_id', '').strip()
        
        from django.utils import timezone
        today = timezone.now().date()
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT AnimalID, AnimalName FROM Animals ORDER BY AnimalName")
            animals = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]
            
            cursor.execute("SELECT VaccinationTypeID, VaccinationName FROM VaccinationTypes ORDER BY VaccinationName")
            types = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]
        
        return render(request, 'animals/vaccination/form.html', {
            'animals': animals,
            'types': types,
            'animal_id': animal_id,
            'today': today,
        })
    
    def post(self, request):
        animal_id = request.POST.get('animal_id', '').strip()
        vaccination_type_id = request.POST.get('vaccination_type_id', '').strip()
        vaccination_date = request.POST.get('vaccination_date', '').strip()
        
        if not animal_id or not vaccination_type_id:
            messages.error(request, 'Заполните обязательные поля')
            return redirect('vaccination_create')
        
        try:
            with connection.cursor() as cursor:
                # Проверяем, существует ли уже такая вакцинация для этого животного
                cursor.execute("""
                    SELECT AnimalVaccinationID 
                    FROM AnimalVaccinations
                    WHERE AnimalID = %s AND VaccinationTypeID = %s
                """, [animal_id, vaccination_type_id])
                
                existing = cursor.fetchone()
                
                if existing:
                    animal_vaccination_id = existing[0]
                else:
                    # Создаем новую связь животного с типом вакцинации
                    cursor.execute("""
                        INSERT INTO AnimalVaccinations (AnimalID, VaccinationTypeID)
                        VALUES (%s, %s)
                    """, [animal_id, vaccination_type_id])
                    
                    # Получаем ID созданной записи (используем OUTPUT для надежности)
                    cursor.execute("""
                        SELECT AnimalVaccinationID 
                        FROM AnimalVaccinations 
                        WHERE AnimalID = %s AND VaccinationTypeID = %s
                    """, [animal_id, vaccination_type_id])
                    result = cursor.fetchone()
                    if not result or not result[0]:
                        raise Exception('Не удалось получить ID созданной вакцинации')
                    animal_vaccination_id = result[0]
                
                # Проверяем, что animal_vaccination_id не None
                if not animal_vaccination_id:
                    raise Exception('AnimalVaccinationID не может быть пустым')
                
                # Если указана дата, создаем запись о вакцинации
                if vaccination_date:
                    cursor.execute("""
                        INSERT INTO VaccinationRecords (AnimalVaccinationID, VaccinationDate)
                        VALUES (%s, %s)
                    """, [animal_vaccination_id, vaccination_date])
            
            messages.success(request, 'Вакцинация успешно добавлена')
            return redirect('vaccinations_list')
        except Exception as e:
            messages.error(request, f'Ошибка при создании вакцинации: {str(e)}')
            return redirect('vaccination_create')


class VaccinationAddRecordView(AdminOrManagerRequiredMixin, View):
    """Добавление записи о вакцинации (даты)"""
    
    def get(self, request, pk):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    av.AnimalVaccinationID,
                    a.AnimalName,
                    vt.VaccinationName
                FROM AnimalVaccinations av
                INNER JOIN Animals a ON av.AnimalID = a.AnimalID
                INNER JOIN VaccinationTypes vt ON av.VaccinationTypeID = vt.VaccinationTypeID
                WHERE av.AnimalVaccinationID = %s
            """, [pk])
            
            row = cursor.fetchone()
            
            if not row:
                messages.error(request, 'Вакцинация не найдена')
                return redirect('vaccinations_list')
            
            vaccination = {
                'id': row[0],
                'animal_name': row[1],
                'type_name': row[2],
            }
        
        from django.utils import timezone
        today = timezone.now().date()
        
        return render(request, 'animals/vaccination/add_record.html', {
            'vaccination': vaccination,
            'today': today,
        })
    
    def post(self, request, pk):
        vaccination_date = request.POST.get('vaccination_date', '').strip()
        
        if not vaccination_date:
            messages.error(request, 'Укажите дату вакцинации')
            return redirect('vaccination_add_record', pk=pk)
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO VaccinationRecords (AnimalVaccinationID, VaccinationDate)
                    VALUES (%s, %s)
                """, [pk, vaccination_date])
            
            messages.success(request, 'Запись о вакцинации успешно добавлена')
            return redirect('vaccination_detail', pk=pk)
        except Exception as e:
            messages.error(request, f'Ошибка при добавлении записи: {str(e)}')
            return redirect('vaccination_add_record', pk=pk)


class VaccinationDeleteView(AdminOrManagerRequiredMixin, View):
    """Удаление вакцинации"""
    
    def post(self, request, pk):
        try:
            with connection.cursor() as cursor:
                # Удаляем записи о вакцинациях
                cursor.execute("DELETE FROM VaccinationRecords WHERE AnimalVaccinationID = %s", [pk])
                # Удаляем связь животного с типом вакцинации
                cursor.execute("DELETE FROM AnimalVaccinations WHERE AnimalVaccinationID = %s", [pk])
            
            messages.success(request, 'Вакцинация успешно удалена')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении вакцинации: {str(e)}')
        
        return redirect('vaccinations_list')


class VaccinationRecordDeleteView(AdminOrManagerRequiredMixin, View):
    """Удаление конкретной записи о вакцинации (даты)"""
    
    def post(self, request, record_id):
        try:
            with connection.cursor() as cursor:
                # Получаем AnimalVaccinationID для редиректа
                cursor.execute("SELECT AnimalVaccinationID FROM VaccinationRecords WHERE RecordID = %s", [record_id])
                row = cursor.fetchone()
                
                if row:
                    animal_vaccination_id = row[0]
                    cursor.execute("DELETE FROM VaccinationRecords WHERE RecordID = %s", [record_id])
                    messages.success(request, 'Запись о вакцинации успешно удалена')
                    return redirect('vaccination_detail', pk=animal_vaccination_id)
                else:
                    messages.error(request, 'Запись не найдена')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении записи: {str(e)}')
        
        return redirect('vaccinations_list')

