from django.shortcuts import render
from django.views import View
from django.db import connection
from django.core.paginator import Paginator
from news.mixins import AdminOrManagerRequiredMixin


class DonationsManagerListView(AdminOrManagerRequiredMixin, View):
    """Список всех пожертвований для менеджера"""
    def get(self, request):
        # Фильтры
        search_query = request.GET.get('q', '').strip()
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        manager_shelter_id = getattr(request, 'manager_shelter_id', None)
        
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    d.DonationID,
                    d.DonationDate,
                    d.Amount,
                    d.Comment,
                    an.AnimalName,
                    an.AnimalID,
                    u.UserID,
                    u.FirstName || ' ' || u.LastName AS UserName,
                    u.Email
                FROM Donations d
                JOIN Animals an ON d.AnimalID = an.AnimalID
                JOIN Users u ON d.UserID = u.UserID
                WHERE 1=1
            """
            params = []

            # Менеджер видит пожертвования только своего приюта
            if getattr(request, 'current_user_role', None) == 'Manager':
                query += " AND an.ShelterID = %s"
                params.append(manager_shelter_id)
            
            if search_query:
                query += " AND (an.AnimalName LIKE %s OR u.FirstName || ' ' || u.LastName LIKE %s OR u.Email LIKE %s)"
                search_param = f'%{search_query}%'
                params.extend([search_param, search_param, search_param])
            
            if date_from:
                query += " AND CAST(d.DonationDate AS DATE) >= %s"
                params.append(date_from)
            
            if date_to:
                query += " AND CAST(d.DonationDate AS DATE) <= %s"
                params.append(date_to)
            
            query += " ORDER BY d.DonationDate DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Подсчитываем статистику
            stats_query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(Amount) as total_amount,
                    AVG(Amount) as avg_amount,
                    MAX(Amount) as max_amount
                FROM Donations
            """
            stats_params = []
            if getattr(request, 'current_user_role', None) == 'Manager':
                stats_query = """
                    SELECT 
                        COUNT(*) as total,
                        SUM(d.Amount) as total_amount,
                        AVG(d.Amount) as avg_amount,
                        MAX(d.Amount) as max_amount
                    FROM Donations d
                    JOIN Animals an ON d.AnimalID = an.AnimalID
                    WHERE an.ShelterID = %s
                """
                stats_params = [manager_shelter_id]
            cursor.execute(stats_query, stats_params)
            stats_row = cursor.fetchone()
            
            stats = {
                'total': stats_row[0] if stats_row else 0,
                'total_amount': float(stats_row[1]) if stats_row[1] else 0.0,
                'avg_amount': float(stats_row[2]) if stats_row[2] else 0.0,
                'max_amount': float(stats_row[3]) if stats_row[3] else 0.0,
            }
        
        donations = []
        for r in rows:
            donation_id, donation_date, amount, comment, animal_name, animal_id, user_id, user_name, email = r
            donations.append({
                'id': donation_id,
                'date': donation_date,
                'amount': float(amount) if amount else 0.0,
                'comment': comment,
                'animal_name': animal_name,
                'animal_id': animal_id,
                'user_id': user_id,
                'user_name': user_name,
                'email': email,
            })
        
        # Пагинация - по 5 записей на страницу
        paginator = Paginator(donations, 5)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'accounts/manager/donations_list.html', {
            'page_obj': page_obj,
            'donations': page_obj,  # Для обратной совместимости
            'stats': stats,
            'search_query': search_query,
            'date_from': date_from,
            'date_to': date_to,
        })

