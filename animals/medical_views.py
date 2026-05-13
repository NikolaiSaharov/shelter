from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.db import connection
from news.mixins import AdminOrManagerRequiredMixin


def _animals_for_request(request):
    manager_shelter_id = getattr(request, 'manager_shelter_id', None)
    with connection.cursor() as cursor:
        if getattr(request, 'current_user_role', None) == 'Manager':
            cursor.execute(
                "SELECT AnimalID, AnimalName FROM Animals WHERE ShelterID = %s ORDER BY AnimalName",
                [manager_shelter_id],
            )
        else:
            cursor.execute("SELECT AnimalID, AnimalName FROM Animals ORDER BY AnimalName")
        return [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]


def _format_diagnosis_date(val):
    if not val:
        return ''
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    s = str(val).strip()
    return s[:10] if len(s) >= 10 else s


def _record_from_post(post, record_id=None):
    """Словарь полей формы для шаблона (совместим с record из БД)."""
    animal_id = post.get('animal_id', '').strip()
    aid = int(animal_id) if animal_id.isdigit() else None
    rec = {
        'animal_id': aid,
        'condition_name': post.get('condition_name', '').strip(),
        'diagnosis_date': post.get('diagnosis_date', '').strip(),
        'treatment': post.get('treatment', '').strip(),
        'status': post.get('status', 'Active').strip(),
        'notes': post.get('notes', '').strip(),
    }
    if record_id is not None:
        rec['id'] = record_id
    return rec


class MedicalRecordsListView(AdminOrManagerRequiredMixin, View):
    """Список медицинских записей для админа/менеджера"""
    
    def get(self, request):
        animal_id = request.GET.get('animal_id', '').strip()
        search_query = request.GET.get('q', '').strip()
        status_filter = request.GET.get('status', '').strip()
        manager_shelter_id = getattr(request, 'manager_shelter_id', None)
        
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    amr.RecordID,
                    amr.ConditionName,
                    amr.DiagnosisDate,
                    amr.Treatment,
                    amr.Status,
                    amr.Notes,
                    a.AnimalID,
                    a.AnimalName
                FROM AnimalMedicalRecords amr
                INNER JOIN Animals a ON amr.AnimalID = a.AnimalID
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
                query += " AND (amr.ConditionName LIKE %s OR amr.Treatment LIKE %s OR a.AnimalName LIKE %s)"
                search_param = f'%{search_query}%'
                params.extend([search_param, search_param, search_param])
            
            if status_filter:
                query += " AND amr.Status = %s"
                params.append(status_filter)
            
            query += " ORDER BY amr.DiagnosisDate DESC, amr.RecordID DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        records = []
        for row in rows:
            records.append({
                'id': row[0],
                'condition': row[1],
                'diagnosis_date': row[2],
                'treatment': row[3],
                'status': row[4],
                'notes': row[5],
                'animal_id': row[6],
                'animal_name': row[7],
            })
        
        # Список животных для фильтра
        with connection.cursor() as cursor:
            if getattr(request, 'current_user_role', None) == 'Manager':
                cursor.execute("SELECT AnimalID, AnimalName FROM Animals WHERE ShelterID = %s ORDER BY AnimalName", [manager_shelter_id])
            else:
                cursor.execute("SELECT AnimalID, AnimalName FROM Animals ORDER BY AnimalName")
            animals = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]
        
        return render(request, 'animals/medical/records_list.html', {
            'records': records,
            'animals': animals,
            'animal_id': animal_id,
            'search_query': search_query,
            'status_filter': status_filter,
        })


class MedicalRecordCreateView(AdminOrManagerRequiredMixin, View):
    """Создание медицинской записи"""
    
    def get(self, request):
        animal_id_raw = request.GET.get('animal_id', '').strip()
        aid = int(animal_id_raw) if animal_id_raw.isdigit() else None
        animals = _animals_for_request(request)
        return render(request, 'animals/medical/record_form.html', {
            'animals': animals,
            'animal_id': animal_id_raw,
            'record': {
                'animal_id': aid,
                'condition_name': '',
                'diagnosis_date': '',
                'treatment': '',
                'status': 'Active',
                'notes': '',
            },
            'errors': [],
        })
    
    def post(self, request):
        animal_id = request.POST.get('animal_id', '').strip()
        condition_name = request.POST.get('condition_name', '').strip()
        diagnosis_date = request.POST.get('diagnosis_date', '').strip()
        treatment = request.POST.get('treatment', '').strip()
        status = request.POST.get('status', 'Active').strip()
        notes = request.POST.get('notes', '').strip()

        errors = []
        if not animal_id or not condition_name:
            errors.append('Заполните обязательные поля: животное и название состояния.')

        if len(condition_name) > 100:
            errors.append('Название состояния не длиннее 100 символов.')
        if len(treatment) > 500:
            errors.append('Поле «Лечение» не длиннее 500 символов.')

        # Ограничение: менеджер может создавать записи только для животных своего приюта
        if not errors and getattr(request, 'current_user_role', None) == 'Manager':
            with connection.cursor() as cursor:
                cursor.execute("SELECT ShelterID FROM Animals WHERE AnimalID=%s", [animal_id])
                r = cursor.fetchone()
            if not r or r[0] != request.manager_shelter_id:
                errors.append('Доступ запрещён: животное относится к другому приюту.')

        if errors:
            record = _record_from_post(request.POST)
            return render(request, 'animals/medical/record_form.html', {
                'animals': _animals_for_request(request),
                'animal_id': animal_id,
                'record': record,
                'errors': errors,
            })

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO AnimalMedicalRecords 
                    (AnimalID, ConditionName, DiagnosisDate, Treatment, Status, Notes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [
                    animal_id,
                    condition_name,
                    diagnosis_date if diagnosis_date else None,
                    treatment if treatment else None,
                    status,
                    notes if notes else None,
                ])
            
            messages.success(request, 'Медицинская запись успешно создана')
            return redirect('medical_records_list')
        except Exception as e:
            return render(request, 'animals/medical/record_form.html', {
                'animals': _animals_for_request(request),
                'animal_id': animal_id,
                'record': _record_from_post(request.POST),
                'errors': [f'Ошибка при создании записи: {str(e)}'],
            })


class MedicalRecordUpdateView(AdminOrManagerRequiredMixin, View):
    """Редактирование медицинской записи"""
    
    def get(self, request, pk):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    RecordID,
                    AnimalID,
                    ConditionName,
                    DiagnosisDate,
                    Treatment,
                    Status,
                    Notes
                FROM AnimalMedicalRecords
                WHERE RecordID = %s
            """, [pk])
            
            row = cursor.fetchone()
            
            if not row:
                messages.error(request, 'Запись не найдена')
                return redirect('medical_records_list')
            
            record = {
                'id': row[0],
                'animal_id': row[1],
                'condition_name': row[2],
                'diagnosis_date': _format_diagnosis_date(row[3]),
                'treatment': row[4],
                'status': row[5],
                'notes': row[6],
            }
            
            animals = _animals_for_request(request)
        
        return render(request, 'animals/medical/record_form.html', {
            'record': record,
            'animals': animals,
            'animal_id': '',
            'errors': [],
        })
    
    def post(self, request, pk):
        animal_id = request.POST.get('animal_id', '').strip()
        condition_name = request.POST.get('condition_name', '').strip()
        diagnosis_date = request.POST.get('diagnosis_date', '').strip()
        treatment = request.POST.get('treatment', '').strip()
        status = request.POST.get('status', 'Active').strip()
        notes = request.POST.get('notes', '').strip()

        errors = []
        if not animal_id or not condition_name:
            errors.append('Заполните обязательные поля: животное и название состояния.')
        if len(condition_name) > 100:
            errors.append('Название состояния не длиннее 100 символов.')
        if len(treatment) > 500:
            errors.append('Поле «Лечение» не длиннее 500 символов.')

        if errors:
            return render(request, 'animals/medical/record_form.html', {
                'record': _record_from_post(request.POST, record_id=pk),
                'animals': _animals_for_request(request),
                'animal_id': animal_id,
                'errors': errors,
            })

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE AnimalMedicalRecords 
                    SET AnimalID = %s,
                        ConditionName = %s,
                        DiagnosisDate = %s,
                        Treatment = %s,
                        Status = %s,
                        Notes = %s
                    WHERE RecordID = %s
                """, [
                    animal_id,
                    condition_name,
                    diagnosis_date if diagnosis_date else None,
                    treatment if treatment else None,
                    status,
                    notes if notes else None,
                    pk,
                ])
            
            messages.success(request, 'Медицинская запись успешно обновлена')
            return redirect('medical_records_list')
        except Exception as e:
            return render(request, 'animals/medical/record_form.html', {
                'record': _record_from_post(request.POST, record_id=pk),
                'animals': _animals_for_request(request),
                'animal_id': animal_id,
                'errors': [f'Ошибка при обновлении записи: {str(e)}'],
            })


class MedicalRecordDeleteView(AdminOrManagerRequiredMixin, View):
    """Удаление медицинской записи"""
    
    def post(self, request, pk):
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM AnimalMedicalRecords WHERE RecordID = %s", [pk])
            
            messages.success(request, 'Медицинская запись успешно удалена')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении записи: {str(e)}')
        
        return redirect('medical_records_list')


