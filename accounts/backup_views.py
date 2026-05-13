from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import connection, transaction
from django.utils import timezone
from django.utils.encoding import smart_str
from animals.mixins import AdminRequiredMixin
from .models import User, UserProfile, Role
from .utils import get_user_id_from_jwt
from animals.models import Animal, AnimalType, Breed, AnimalStatus, AnimalCharacter
from news.models import News
import json
import decimal
from datetime import datetime, date


class DecimalEncoder(json.JSONEncoder):
    """Кастомный энкодер для Decimal и datetime"""
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


class BackupCreateView(AdminRequiredMixin, View):
    """Создание бэкапа данных (админ)"""
    
    def get(self, request):
        try:
            backup_data = {
                'metadata': {
                    'created_at': timezone.now().isoformat(),
                    'created_by': get_user_id_from_jwt(request),
                    'version': '1.0'
                },
                'data': {}
            }
            
            # Справочники (Roles, AnimalTypes, Breeds, AnimalStatuses, AnimalCharacters)
            backup_data['data']['Roles'] = [
                {
                    'RoleID': r.role_id,
                    'RoleName': r.role_name
                }
                for r in Role.objects.all()
            ]
            
            backup_data['data']['AnimalTypes'] = [
                {
                    'TypeID': t.type_id,
                    'TypeName': t.type_name
                }
                for t in AnimalType.objects.all()
            ]
            
            backup_data['data']['Breeds'] = [
                {
                    'BreedID': b.breed_id,
                    'BreedName': b.breed_name,
                    'TypeID': b.type_id
                }
                for b in Breed.objects.all()
            ]
            
            backup_data['data']['AnimalStatuses'] = [
                {
                    'StatusID': s.status_id,
                    'StatusName': s.status_name
                }
                for s in AnimalStatus.objects.all()
            ]
            
            backup_data['data']['AnimalCharacters'] = [
                {
                    'CharacterID': c.character_id,
                    'CharacterName': c.character_name,
                    'Description': c.description
                }
                for c in AnimalCharacter.objects.all()
            ]
            
            # Основные данные (Users, UserProfiles, Animals, News)
            backup_data['data']['Users'] = [
                {
                    'UserID': u.user_id,
                    'Email': u.email,
                    'PasswordHash': u.password_hash,
                    'FirstName': u.first_name,
                    'LastName': u.last_name,
                    'MiddleName': u.middle_name,
                    'Phone': u.phone,
                    'RegistrationDate': u.registration_date.isoformat() if u.registration_date else None,
                    'RoleID': u.role_id
                }
                for u in User.objects.select_related('role').all()
            ]
            
            backup_data['data']['UserProfiles'] = [
                {
                    'ProfileID': p.profile_id,
                    'UserID': p.user_id,
                    'HomeAddress': p.home_address,
                    'DateOfBirth': p.date_of_birth.isoformat() if p.date_of_birth else None,
                    'ProfilePicture': p.profile_picture,
                    'CreatedDate': p.created_date.isoformat() if p.created_date else None,
                    'UpdatedDate': p.updated_date.isoformat() if p.updated_date else None
                }
                for p in UserProfile.objects.all()
            ]
            
            backup_data['data']['Animals'] = [
                {
                    'AnimalID': a.animal_id,
                    'AnimalName': a.animal_name,
                    'Age': a.age,
                    'Gender': a.gender,
                    'Vaccinated': a.vaccinated,
                    'Description': a.description,
                    'ImagePath': a.image_path,
                    'StatusID': a.status_id,
                    'BreedID': a.breed_id,
                    'CharacterID': a.character_id,
                    'Height': float(a.height) if a.height else None,
                    'AnimalWeight': float(a.animal_weight) if a.animal_weight else None,
                    'AdmissionDate': a.admission_date.isoformat() if a.admission_date else None
                }
                for a in Animal.objects.select_related('breed', 'status', 'character').all()
            ]
            
            backup_data['data']['News'] = [
                {
                    'NewsID': n.news_id,
                    'UserID': n.user_id,
                    'Title': n.title,
                    'Content': n.content,
                    'PostDate': n.post_date.isoformat() if n.post_date else None,
                    'IsPublished': n.is_published,
                    'ImagePath': n.image_path
                }
                for n in News.objects.all()
            ]
            
            # Медицинские записи и вакцинации (используем raw SQL)
            from django.db import connection
            with connection.cursor() as cursor:
                # Медицинские записи
                cursor.execute("""
                    SELECT RecordID, AnimalID, ConditionName, DiagnosisDate, Treatment, Status, Notes
                    FROM AnimalMedicalRecords
                """)
                backup_data['data']['AnimalMedicalRecords'] = []
                for row in cursor.fetchall():
                    backup_data['data']['AnimalMedicalRecords'].append({
                        'RecordID': row[0],
                        'AnimalID': row[1],
                        'ConditionName': row[2],
                        'DiagnosisDate': row[3].isoformat() if row[3] else None,
                        'Treatment': row[4],
                        'Status': row[5],
                        'Notes': row[6]
                    })
                
                # Вакцинации (связи животных с типами вакцинаций)
                cursor.execute("""
                    SELECT AnimalVaccinationID, AnimalID, VaccinationTypeID
                    FROM AnimalVaccinations
                """)
                backup_data['data']['AnimalVaccinations'] = []
                for row in cursor.fetchall():
                    backup_data['data']['AnimalVaccinations'].append({
                        'AnimalVaccinationID': row[0],
                        'AnimalID': row[1],
                        'VaccinationTypeID': row[2]
                    })
                
                # Записи о проведенных вакцинациях
                cursor.execute("""
                    SELECT RecordID, AnimalVaccinationID, VaccinationDate
                    FROM VaccinationRecords
                """)
                backup_data['data']['VaccinationRecords'] = []
                for row in cursor.fetchall():
                    backup_data['data']['VaccinationRecords'].append({
                        'RecordID': row[0],
                        'AnimalVaccinationID': row[1],
                        'VaccinationDate': row[2].isoformat() if row[2] else None
                    })
                
                # Сообщения
                cursor.execute("""
                    SELECT MessageID, SenderID, SubjectMessages, MessageText, SendDate, ParentMessageID, IsRead, RecipientRole
                    FROM Messages
                """)
                backup_data['data']['Messages'] = []
                for row in cursor.fetchall():
                    backup_data['data']['Messages'].append({
                        'MessageID': row[0],
                        'SenderID': row[1],
                        'SubjectMessages': row[2],
                        'MessageText': row[3],
                        'SendDate': row[4].isoformat() if row[4] else None,
                        'ParentMessageID': row[5],
                        'IsRead': row[6] if len(row) > 6 else False,
                        'RecipientRole': row[7] if len(row) > 7 else None
                    })
                
                # Пожертвования
                cursor.execute("""
                    SELECT DonationID, UserID, AnimalID, Amount, DonationDate, Comment, IsApproved
                    FROM Donations
                """)
                backup_data['data']['Donations'] = []
                for row in cursor.fetchall():
                    backup_data['data']['Donations'].append({
                        'DonationID': row[0],
                        'UserID': row[1],
                        'AnimalID': row[2],
                        'Amount': float(row[3]) if row[3] else None,
                        'DonationDate': row[4].isoformat() if row[4] else None,
                        'Comment': row[5],
                        'IsApproved': row[6] if len(row) > 6 else None
                    })
                
                # Заявки на усыновление
                cursor.execute("""
                    SELECT a.ApplicationID, a.UserID, a.AnimalID, a.ApplicationDate, a.StatusID, ast.StatusName, 
                           a.Reason, a.Experience, a.HousingConditions, a.Comment
                    FROM Applications a
                    JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                """)
                backup_data['data']['Applications'] = []
                for row in cursor.fetchall():
                    # Для обратной совместимости сохраняем IsApproved на основе StatusName
                    status_name = row[5] if len(row) > 5 else None
                    is_approved = (status_name == 'Approved') if status_name else None
                    
                    backup_data['data']['Applications'].append({
                        'ApplicationID': row[0],
                        'UserID': row[1],
                        'AnimalID': row[2],
                        'ApplicationDate': row[3].isoformat() if row[3] else None,
                        'StatusID': row[4],
                        'StatusName': status_name,
                        'IsApproved': is_approved,  # Для обратной совместимости
                        'Reason': row[6] if len(row) > 6 else None,
                        'Experience': row[7] if len(row) > 7 else None,
                        'HousingConditions': row[8] if len(row) > 8 else None,
                        'Comment': row[9] if len(row) > 9 else None
                    })
            
            # Преобразуем в JSON
            json_data = json.dumps(backup_data, ensure_ascii=False, indent=2, cls=DecimalEncoder)
            
            # Создаем HTTP ответ для скачивания файла
            filename = f"backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
            response = HttpResponse(json_data, content_type='application/json; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            messages.success(request, 'Бэкап успешно создан и готов к скачиванию')
            return response
            
        except Exception as e:
            messages.error(request, f'Ошибка при создании бэкапа: {str(e)}')
            return redirect('profile')


class BackupRestoreView(AdminRequiredMixin, View):
    """Восстановление данных из бэкапа (админ)"""
    
    def get(self, request):
        return render(request, 'accounts/backup_restore.html')
    
    def post(self, request):
        if 'backup_file' not in request.FILES:
            messages.error(request, 'Файл не выбран')
            return render(request, 'accounts/backup_restore.html')
        
        backup_file = request.FILES['backup_file']
        
        try:
            # Читаем и парсим JSON
            file_content = backup_file.read().decode('utf-8')
            backup_data = json.loads(file_content)
            
            if 'data' not in backup_data:
                messages.error(request, 'Неверный формат файла бэкапа')
                return render(request, 'accounts/backup_restore.html')
            
            # Используем Django транзакцию для безопасности
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Отключаем триггеры и проверку внешних ключей для PostgreSQL
                    try:
                        cursor.execute("SET session_replication_role = 'replica';")
                    except Exception as e:
                        print(f"Warning: Could not set session_replication_role: {e}")
                    
                    try:
                        # Список таблиц в правильном порядке для удаления (в нижнем регистре)
                        tables_in_order = [
                            'vaccinationrecords',
                            'animalvaccinations', 
                            'animalmedicalrecords',
                            'meetingparticipants',
                            'videomeetings',
                            'applications',
                            'donations',
                            'messages',
                            'news',
                            'userprofiles',
                            'animals',
                            'users',
                            'breeds',
                            'animaltypes',
                            'animalstatuses',
                            'animalcharacters',
                            'roles'
                        ]
                        
                        # Очищаем таблицы (включая сброс последовательностей)
                        for table in tables_in_order:
                            try:
                                # Проверяем существование таблицы
                                cursor.execute(f"""
                                    SELECT EXISTS (
                                        SELECT FROM information_schema.tables 
                                        WHERE table_name = '{table}'
                                    )
                                """)
                                if cursor.fetchone()[0]:
                                    cursor.execute(f'TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;')
                                    print(f"Truncated table: {table}")
                                else:
                                    print(f"Table {table} does not exist, skipping")
                            except Exception as e:
                                print(f"Could not truncate {table}: {e}")
                        
                        # 1. Восстанавливаем справочники
                        # Roles
                        if 'Roles' in backup_data['data'] and backup_data['data']['Roles']:
                            try:
                                for role in backup_data['data']['Roles']:
                                    cursor.execute("""
                                        INSERT INTO roles (roleid, rolename)
                                        VALUES (%s, %s)
                                        ON CONFLICT (roleid) DO UPDATE SET
                                            rolename = EXCLUDED.rolename
                                    """, [role['RoleID'], role['RoleName']])
                                print(f"Restored {len(backup_data['data']['Roles'])} roles")
                            except Exception as e:
                                print(f"Error restoring Roles: {e}")
                                raise
                        
                        # AnimalTypes
                        if 'AnimalTypes' in backup_data['data'] and backup_data['data']['AnimalTypes']:
                            try:
                                for atype in backup_data['data']['AnimalTypes']:
                                    cursor.execute("""
                                        INSERT INTO animaltypes (typeid, typename)
                                        VALUES (%s, %s)
                                        ON CONFLICT (typeid) DO UPDATE SET
                                            typename = EXCLUDED.typename
                                    """, [atype['TypeID'], atype['TypeName']])
                                print(f"Restored {len(backup_data['data']['AnimalTypes'])} animal types")
                            except Exception as e:
                                print(f"Error restoring AnimalTypes: {e}")
                        
                        # AnimalStatuses
                        if 'AnimalStatuses' in backup_data['data'] and backup_data['data']['AnimalStatuses']:
                            try:
                                for status in backup_data['data']['AnimalStatuses']:
                                    cursor.execute("""
                                        INSERT INTO animalstatuses (statusid, statusname)
                                        VALUES (%s, %s)
                                        ON CONFLICT (statusid) DO UPDATE SET
                                            statusname = EXCLUDED.statusname
                                    """, [status['StatusID'], status['StatusName']])
                                print(f"Restored {len(backup_data['data']['AnimalStatuses'])} statuses")
                            except Exception as e:
                                print(f"Error restoring AnimalStatuses: {e}")
                        
                        # AnimalCharacters
                        if 'AnimalCharacters' in backup_data['data'] and backup_data['data']['AnimalCharacters']:
                            try:
                                for char in backup_data['data']['AnimalCharacters']:
                                    cursor.execute("""
                                        INSERT INTO animalcharacters (characterid, charactername, description)
                                        VALUES (%s, %s, %s)
                                        ON CONFLICT (characterid) DO UPDATE SET
                                            charactername = EXCLUDED.charactername,
                                            description = EXCLUDED.description
                                    """, [char['CharacterID'], char['CharacterName'], char.get('Description')])
                                print(f"Restored {len(backup_data['data']['AnimalCharacters'])} characters")
                            except Exception as e:
                                print(f"Error restoring AnimalCharacters: {e}")
                        
                        # Breeds
                        if 'Breeds' in backup_data['data'] and backup_data['data']['Breeds']:
                            try:
                                for breed in backup_data['data']['Breeds']:
                                    cursor.execute("""
                                        INSERT INTO breeds (breedid, breedname, typeid)
                                        VALUES (%s, %s, %s)
                                        ON CONFLICT (breedid) DO UPDATE SET
                                            breedname = EXCLUDED.breedname,
                                            typeid = EXCLUDED.typeid
                                    """, [breed['BreedID'], breed['BreedName'], breed['TypeID']])
                                print(f"Restored {len(backup_data['data']['Breeds'])} breeds")
                            except Exception as e:
                                print(f"Error restoring Breeds: {e}")
                        
                        # 2. Восстанавливаем Users
                        if 'Users' in backup_data['data'] and backup_data['data']['Users']:
                            try:
                                for user in backup_data['data']['Users']:
                                    reg_date = user.get('RegistrationDate')
                                    if reg_date:
                                        try:
                                            reg_date = datetime.fromisoformat(reg_date.replace('Z', '+00:00'))
                                        except:
                                            reg_date = None
                                    
                                    cursor.execute("""
                                        INSERT INTO users (userid, email, passwordhash, firstname, lastname, middlename, phone, registrationdate, roleid)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (userid) DO UPDATE SET
                                            email = EXCLUDED.email,
                                            passwordhash = EXCLUDED.passwordhash,
                                            firstname = EXCLUDED.firstname,
                                            lastname = EXCLUDED.lastname,
                                            middlename = EXCLUDED.middlename,
                                            phone = EXCLUDED.phone,
                                            registrationdate = EXCLUDED.registrationdate,
                                            roleid = EXCLUDED.roleid
                                    """, [
                                        user['UserID'],
                                        user['Email'],
                                        user['PasswordHash'],
                                        user['FirstName'],
                                        user['LastName'],
                                        user.get('MiddleName'),
                                        user['Phone'],
                                        reg_date,
                                        user['RoleID']
                                    ])
                                print(f"Restored {len(backup_data['data']['Users'])} users")
                            except Exception as e:
                                print(f"Error restoring Users: {e}")
                                raise
                        
                        # 3. Восстанавливаем UserProfiles
                        if 'UserProfiles' in backup_data['data'] and backup_data['data']['UserProfiles']:
                            try:
                                for profile in backup_data['data']['UserProfiles']:
                                    dob = profile.get('DateOfBirth')
                                    if dob:
                                        try:
                                            dob = date.fromisoformat(dob) if isinstance(dob, str) else dob
                                        except:
                                            dob = None
                                    
                                    created_date = profile.get('CreatedDate')
                                    if created_date:
                                        try:
                                            created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                                        except:
                                            created_date = None
                                    
                                    updated_date = profile.get('UpdatedDate')
                                    if updated_date:
                                        try:
                                            updated_date = datetime.fromisoformat(updated_date.replace('Z', '+00:00'))
                                        except:
                                            updated_date = None
                                    
                                    cursor.execute("""
                                        INSERT INTO userprofiles (profileid, userid, homeaddress, dateofbirth, profilepicture, createddate, updateddate)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (profileid) DO UPDATE SET
                                            userid = EXCLUDED.userid,
                                            homeaddress = EXCLUDED.homeaddress,
                                            dateofbirth = EXCLUDED.dateofbirth,
                                            profilepicture = EXCLUDED.profilepicture,
                                            createddate = EXCLUDED.createddate,
                                            updateddate = EXCLUDED.updateddate
                                    """, [
                                        profile['ProfileID'],
                                        profile['UserID'],
                                        profile.get('HomeAddress'),
                                        dob,
                                        profile.get('ProfilePicture'),
                                        created_date,
                                        updated_date
                                    ])
                                print(f"Restored {len(backup_data['data']['UserProfiles'])} user profiles")
                            except Exception as e:
                                print(f"Error restoring UserProfiles: {e}")
                        
                        # 4. Восстанавливаем Animals
                        if 'Animals' in backup_data['data'] and backup_data['data']['Animals']:
                            try:
                                for animal in backup_data['data']['Animals']:
                                    admission_date = animal.get('AdmissionDate')
                                    if admission_date:
                                        try:
                                            admission_date = date.fromisoformat(admission_date) if isinstance(admission_date, str) else admission_date
                                        except:
                                            admission_date = None
                                    
                                    cursor.execute("""
                                        INSERT INTO animals (animalid, animalname, age, gender, vaccinated, description, imagepath, statusid, breedid, characterid, height, animalweight, admissiondate)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (animalid) DO UPDATE SET
                                            animalname = EXCLUDED.animalname,
                                            age = EXCLUDED.age,
                                            gender = EXCLUDED.gender,
                                            vaccinated = EXCLUDED.vaccinated,
                                            description = EXCLUDED.description,
                                            imagepath = EXCLUDED.imagepath,
                                            statusid = EXCLUDED.statusid,
                                            breedid = EXCLUDED.breedid,
                                            characterid = EXCLUDED.characterid,
                                            height = EXCLUDED.height,
                                            animalweight = EXCLUDED.animalweight,
                                            admissiondate = EXCLUDED.admissiondate
                                    """, [
                                        animal['AnimalID'],
                                        animal['AnimalName'],
                                        animal['Age'],
                                        animal['Gender'],
                                        animal['Vaccinated'],
                                        animal.get('Description'),
                                        animal.get('ImagePath'),
                                        animal['StatusID'],
                                        animal['BreedID'],
                                        animal.get('CharacterID'),
                                        animal.get('Height'),
                                        animal.get('AnimalWeight'),
                                        admission_date
                                    ])
                                print(f"Restored {len(backup_data['data']['Animals'])} animals")
                            except Exception as e:
                                print(f"Error restoring Animals: {e}")
                        
                        # 5. Восстанавливаем News
                        if 'News' in backup_data['data'] and backup_data['data']['News']:
                            try:
                                for news in backup_data['data']['News']:
                                    post_date = news.get('PostDate')
                                    if post_date:
                                        try:
                                            post_date = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
                                        except:
                                            post_date = None
                                    
                                    cursor.execute("""
                                        INSERT INTO news (newsid, userid, title, content, postdate, ispublished, imagepath)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (newsid) DO UPDATE SET
                                            userid = EXCLUDED.userid,
                                            title = EXCLUDED.title,
                                            content = EXCLUDED.content,
                                            postdate = EXCLUDED.postdate,
                                            ispublished = EXCLUDED.ispublished,
                                            imagepath = EXCLUDED.imagepath
                                    """, [
                                        news['NewsID'],
                                        news['UserID'],
                                        news['Title'],
                                        news['Content'],
                                        post_date,
                                        news['IsPublished'],
                                        news.get('ImagePath')
                                    ])
                                print(f"Restored {len(backup_data['data']['News'])} news items")
                            except Exception as e:
                                print(f"Error restoring News: {e}")
                        
                        # 6. Восстанавливаем медицинские записи
                        if 'AnimalMedicalRecords' in backup_data['data'] and backup_data['data']['AnimalMedicalRecords']:
                            try:
                                for record in backup_data['data']['AnimalMedicalRecords']:
                                    diagnosis_date = record.get('DiagnosisDate')
                                    if diagnosis_date:
                                        try:
                                            diagnosis_date = date.fromisoformat(diagnosis_date) if isinstance(diagnosis_date, str) else diagnosis_date
                                        except:
                                            diagnosis_date = None
                                    
                                    cursor.execute("""
                                        INSERT INTO animalmedicalrecords (recordid, animalid, conditionname, diagnosisdate, treatment, status, notes)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (recordid) DO UPDATE SET
                                            animalid = EXCLUDED.animalid,
                                            conditionname = EXCLUDED.conditionname,
                                            diagnosisdate = EXCLUDED.diagnosisdate,
                                            treatment = EXCLUDED.treatment,
                                            status = EXCLUDED.status,
                                            notes = EXCLUDED.notes
                                    """, [
                                        record['RecordID'],
                                        record['AnimalID'],
                                        record['ConditionName'],
                                        diagnosis_date,
                                        record.get('Treatment'),
                                        record.get('Status'),
                                        record.get('Notes')
                                    ])
                                print(f"Restored {len(backup_data['data']['AnimalMedicalRecords'])} medical records")
                            except Exception as e:
                                print(f"Error restoring AnimalMedicalRecords: {e}")
                        
                        # 7. Восстанавливаем вакцинации
                        if 'AnimalVaccinations' in backup_data['data'] and backup_data['data']['AnimalVaccinations']:
                            try:
                                for vaccination in backup_data['data']['AnimalVaccinations']:
                                    cursor.execute("""
                                        INSERT INTO animalvaccinations (animalvaccinationid, animalid, vaccinationtypeid)
                                        VALUES (%s, %s, %s)
                                        ON CONFLICT (animalvaccinationid) DO UPDATE SET
                                            animalid = EXCLUDED.animalid,
                                            vaccinationtypeid = EXCLUDED.vaccinationtypeid
                                    """, [
                                        vaccination['AnimalVaccinationID'],
                                        vaccination['AnimalID'],
                                        vaccination['VaccinationTypeID']
                                    ])
                                print(f"Restored {len(backup_data['data']['AnimalVaccinations'])} vaccinations")
                            except Exception as e:
                                print(f"Error restoring AnimalVaccinations: {e}")
                        
                        # 8. Восстанавливаем записи о вакцинациях
                        if 'VaccinationRecords' in backup_data['data'] and backup_data['data']['VaccinationRecords']:
                            try:
                                for record in backup_data['data']['VaccinationRecords']:
                                    vaccination_date = record.get('VaccinationDate')
                                    if vaccination_date:
                                        try:
                                            vaccination_date = date.fromisoformat(vaccination_date) if isinstance(vaccination_date, str) else vaccination_date
                                        except:
                                            vaccination_date = None
                                    
                                    cursor.execute("""
                                        INSERT INTO vaccinationrecords (recordid, animalvaccinationid, vaccinationdate)
                                        VALUES (%s, %s, %s)
                                        ON CONFLICT (recordid) DO UPDATE SET
                                            animalvaccinationid = EXCLUDED.animalvaccinationid,
                                            vaccinationdate = EXCLUDED.vaccinationdate
                                    """, [
                                        record['RecordID'],
                                        record['AnimalVaccinationID'],
                                        vaccination_date
                                    ])
                                print(f"Restored {len(backup_data['data']['VaccinationRecords'])} vaccination records")
                            except Exception as e:
                                print(f"Error restoring VaccinationRecords: {e}")
                        
                        # 9. Восстанавливаем сообщения
                        if 'Messages' in backup_data['data'] and backup_data['data']['Messages']:
                            try:
                                for message in backup_data['data']['Messages']:
                                    send_date = message.get('SendDate')
                                    if send_date:
                                        try:
                                            send_date = datetime.fromisoformat(send_date.replace('Z', '+00:00'))
                                        except:
                                            send_date = None
                                    
                                    cursor.execute("""
                                        INSERT INTO messages (messageid, senderid, subjectmessages, messagetext, senddate, parentmessageid, isread, recipientrole)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (messageid) DO UPDATE SET
                                            senderid = EXCLUDED.senderid,
                                            subjectmessages = EXCLUDED.subjectmessages,
                                            messagetext = EXCLUDED.messagetext,
                                            senddate = EXCLUDED.senddate,
                                            parentmessageid = EXCLUDED.parentmessageid,
                                            isread = EXCLUDED.isread,
                                            recipientrole = EXCLUDED.recipientrole
                                    """, [
                                        message['MessageID'],
                                        message['SenderID'],
                                        message.get('SubjectMessages'),
                                        message.get('MessageText'),
                                        send_date,
                                        message.get('ParentMessageID'),
                                        message.get('IsRead', False),
                                        message.get('RecipientRole')
                                    ])
                                print(f"Restored {len(backup_data['data']['Messages'])} messages")
                            except Exception as e:
                                print(f"Error restoring Messages: {e}")
                        
                        # 10. Восстанавливаем пожертвования
                        if 'Donations' in backup_data['data'] and backup_data['data']['Donations']:
                            try:
                                for donation in backup_data['data']['Donations']:
                                    donation_date = donation.get('DonationDate')
                                    if donation_date:
                                        try:
                                            donation_date = datetime.fromisoformat(donation_date.replace('Z', '+00:00'))
                                        except:
                                            donation_date = None
                                    
                                    cursor.execute("""
                                        INSERT INTO donations (donationid, userid, animalid, amount, donationdate, comment, isapproved)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (donationid) DO UPDATE SET
                                            userid = EXCLUDED.userid,
                                            animalid = EXCLUDED.animalid,
                                            amount = EXCLUDED.amount,
                                            donationdate = EXCLUDED.donationdate,
                                            comment = EXCLUDED.comment,
                                            isapproved = EXCLUDED.isapproved
                                    """, [
                                        donation['DonationID'],
                                        donation['UserID'],
                                        donation['AnimalID'],
                                        donation.get('Amount'),
                                        donation_date,
                                        donation.get('Comment'),
                                        donation.get('IsApproved', 1)
                                    ])
                                print(f"Restored {len(backup_data['data']['Donations'])} donations")
                            except Exception as e:
                                print(f"Error restoring Donations: {e}")
                        
                        # 11. Восстанавливаем заявки на усыновление
                        if 'Applications' in backup_data['data'] and backup_data['data']['Applications']:
                            try:
                                # Получаем статусы
                                cursor.execute("SELECT statusid FROM animalstatuses WHERE statusname = 'Пристроен'")
                                adopted_status_row = cursor.fetchone()
                                adopted_status_id = adopted_status_row[0] if adopted_status_row else None
                                
                                approved_animals = []
                                
                                for application in backup_data['data']['Applications']:
                                    app_date = application.get('ApplicationDate')
                                    if app_date:
                                        try:
                                            app_date = datetime.fromisoformat(app_date.replace('Z', '+00:00'))
                                        except:
                                            app_date = None
                                    
                                    # Определяем StatusID
                                    status_id = application.get('StatusID')
                                    if not status_id and 'StatusName' in application:
                                        cursor.execute("SELECT statusid FROM applicationstatuses WHERE statusname = %s", [application['StatusName']])
                                        status_row = cursor.fetchone()
                                        status_id = status_row[0] if status_row else None
                                    
                                    if not status_id:
                                        cursor.execute("SELECT statusid FROM applicationstatuses WHERE statusname = 'Pending'")
                                        status_row = cursor.fetchone()
                                        status_id = status_row[0] if status_row else 1
                                    
                                    cursor.execute("""
                                        INSERT INTO applications (applicationid, userid, animalid, applicationdate, statusid, reason, experience, housingconditions, comment)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (applicationid) DO UPDATE SET
                                            userid = EXCLUDED.userid,
                                            animalid = EXCLUDED.animalid,
                                            applicationdate = EXCLUDED.applicationdate,
                                            statusid = EXCLUDED.statusid,
                                            reason = EXCLUDED.reason,
                                            experience = EXCLUDED.experience,
                                            housingconditions = EXCLUDED.housingconditions,
                                            comment = EXCLUDED.comment
                                    """, [
                                        application['ApplicationID'],
                                        application['UserID'],
                                        application['AnimalID'],
                                        app_date,
                                        status_id,
                                        application.get('Reason'),
                                        application.get('Experience'),
                                        application.get('HousingConditions'),
                                        application.get('Comment')
                                    ])
                                    
                                    # Проверяем, одобрена ли заявка
                                    status_name = application.get('StatusName', '')
                                    is_approved = application.get('IsApproved', False)
                                    if (status_name == 'Approved' or is_approved) and adopted_status_id:
                                        approved_animals.append(application['AnimalID'])
                                
                                # Обновляем статус животных
                                if approved_animals and adopted_status_id:
                                    unique_animal_ids = list(set(approved_animals))
                                    for animal_id in unique_animal_ids:
                                        cursor.execute("""
                                            UPDATE animals 
                                            SET statusid = %s
                                            WHERE animalid = %s AND statusid != %s
                                        """, [adopted_status_id, animal_id, adopted_status_id])
                                
                                print(f"Restored {len(backup_data['data']['Applications'])} applications")
                            except Exception as e:
                                print(f"Error restoring Applications: {e}")
                        
                        messages.success(request, 'Данные успешно восстановлены из бэкапа')
                    
                    except Exception as e:
                        print(f"Restore error: {str(e)}")
                        raise
                    
                    finally:
                        # Восстанавливаем проверку внешних ключей
                        try:
                            cursor.execute("SET session_replication_role = 'origin';")
                        except Exception as e:
                            print(f"Warning: Could not restore session_replication_role: {e}")
            
            return redirect('profile')
            
        except json.JSONDecodeError:
            messages.error(request, 'Ошибка: файл не является валидным JSON')
            return render(request, 'accounts/backup_restore.html')
        except Exception as e:
            messages.error(request, f'Ошибка при восстановлении: {str(e)}')
            return render(request, 'accounts/backup_restore.html')