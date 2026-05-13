from django.shortcuts import render
from django.views import View
from django.http import HttpResponse
from django.db import connection
from django.utils import timezone
from datetime import datetime, timedelta
from news.mixins import AdminOrManagerRequiredMixin
from accounts.utils import get_user_id_from_jwt
import io
import csv

# Попытка импортировать reportlab (опционально)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# Попытка импортировать matplotlib (опционально)
try:
    import matplotlib
    matplotlib.use('Agg')  # Используем backend без GUI
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def _get_user_role(user_id: int):
    """Получает роль пользователя из базы данных"""
    with connection.cursor() as cur:
        cur.execute(
            "SELECT r.RoleName FROM Users u JOIN Roles r ON u.RoleID=r.RoleID WHERE u.UserID=%s",
            [user_id]
        )
        row = cur.fetchone()
        return row[0] if row else None


class StatisticsView(AdminOrManagerRequiredMixin, View):
    """Страница статистики для менеджера"""
    def get(self, request):
        user_id = get_user_id_from_jwt(request)
        if not user_id:
            return render(request, 'accounts/statistics.html', {'error': 'Необходима авторизация'})
        
        # Получаем статистику из базы данных
        stats = self._get_statistics()
        
        return render(request, 'accounts/statistics.html', {
            'stats': stats,
        })
    
    def _get_statistics(self):
        """Собирает статистику из базы данных"""
        stats = {}
        
        with connection.cursor() as cursor:
            # Общая статистика по животным
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_animals,
                    SUM(CASE WHEN StatusID = 1 THEN 1 ELSE 0 END) as available,
                    SUM(CASE WHEN StatusID != 1 THEN 1 ELSE 0 END) as not_available
                FROM Animals
            """)
            row = cursor.fetchone()
            stats['animals'] = {
                'total': row[0] if row else 0,
                'available': row[1] if row else 0,
                'not_available': row[2] if row else 0,
            }
            
            # Статистика по статусам животных
            cursor.execute("""
                SELECT s.StatusName, COUNT(a.AnimalID) as count
                FROM AnimalStatuses s
                LEFT JOIN Animals a ON s.StatusID = a.StatusID
                GROUP BY s.StatusID, s.StatusName
                ORDER BY count DESC
            """)
            stats['animal_statuses'] = [{'name': r[0], 'count': r[1]} for r in cursor.fetchall()]
            
            # Статистика по типам животных
            cursor.execute("""
                SELECT
                    t.TypeName,
                    COALESCE((SELECT COUNT(*) FROM Animals a 
                     JOIN Breeds b ON a.BreedID = b.BreedID 
                     WHERE b.TypeID = t.TypeID), 0) as count
                FROM AnimalTypes t
                ORDER BY count DESC
                LIMIT 5
            """)
            stats['animal_types'] = [{'name': r[0], 'count': r[1]} for r in cursor.fetchall()]
            
            # Статистика по пользователям
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_users,
                    SUM(CASE WHEN r.RoleName = 'Guest' THEN 1 ELSE 0 END) as guests,
                    SUM(CASE WHEN r.RoleName = 'Manager' THEN 1 ELSE 0 END) as managers,
                    SUM(CASE WHEN r.RoleName = 'Admin' THEN 1 ELSE 0 END) as admins
                FROM Users u
                JOIN Roles r ON u.RoleID = r.RoleID
            """)
            row = cursor.fetchone()
            stats['users'] = {
                'total': row[0] if row else 0,
                'guests': row[1] if row else 0,
                'managers': row[2] if row else 0,
                'admins': row[3] if row else 0,
            }
            
            # Статистика по заявкам
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_applications,
                    SUM(CASE WHEN ast.StatusName = 'Approved' THEN 1 ELSE 0 END) as approved,
                    SUM(CASE WHEN ast.StatusName = 'Pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN ast.StatusName = 'Rejected' THEN 1 ELSE 0 END) as rejected
                FROM Applications a
                JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
            """)
            row = cursor.fetchone()
            stats['applications'] = {
                'total': row[0] if row else 0,
                'approved': row[1] if row else 0,
                'pending': row[2] if row else 0,
            }
            
            # Статистика по пожертвованиям
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_donations,
                    SUM(Amount) as total_amount,
                    AVG(Amount) as avg_amount,
                    MAX(Amount) as max_amount
                FROM Donations
            """)
            row = cursor.fetchone()
            stats['donations'] = {
                'total': row[0] if row else 0,
                'total_amount': float(row[1]) if row[1] else 0.0,
                'avg_amount': float(row[2]) if row[2] else 0.0,
                'max_amount': float(row[3]) if row[3] else 0.0,
            }
            
            # Статистика по новостям
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_news,
                    SUM(CASE WHEN IsPublished = TRUE THEN 1 ELSE 0 END) as published,
                    SUM(CASE WHEN IsPublished = FALSE THEN 1 ELSE 0 END) as unpublished
                FROM News
            """)
            row = cursor.fetchone()
            stats['news'] = {
                'total': row[0] if row else 0,
                'published': row[1] if row else 0,
                'unpublished': row[2] if row else 0,
            }
            
            # Статистика по встречам (за последние 30 дней)
            try:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM VideoMeetings 
                    WHERE ScheduledDateTime >= (NOW() - INTERVAL '30 days')
                """)
                row = cursor.fetchone()
                stats['meetings_30_days'] = row[0] if row else 0
            except Exception:
                # Если таблица VideoMeetings не существует, ставим 0
                stats['meetings_30_days'] = 0
            
            # Статистика по новым регистрациям (за последние 30 дней)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM Users 
                WHERE RegistrationDate >= (NOW() - INTERVAL '30 days')
            """)
            row = cursor.fetchone()
            stats['new_users_30_days'] = row[0] if row else 0
            
            # Статистика по заявкам за последние 30 дней
            cursor.execute("""
                SELECT COUNT(*) 
                FROM Applications 
                WHERE ApplicationDate >= (NOW() - INTERVAL '30 days')
            """)
            row = cursor.fetchone()
            stats['new_applications_30_days'] = row[0] if row else 0
            
            # Статистика по пожертвованиям за последние 30 дней
            cursor.execute("""
                SELECT 
                    COUNT(*) as count,
                    SUM(Amount) as total
                FROM Donations 
                WHERE DonationDate >= (NOW() - INTERVAL '30 days')
            """)
            row = cursor.fetchone()
            stats['donations_30_days'] = {
                'count': row[0] if row else 0,
                'total': float(row[1]) if row[1] else 0.0,
            }
            
            # Статистика по пожертвованиям за последние 6 месяцев
            month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
            donations_by_month = []
            current_date = timezone.now()
            
            for i in range(5, -1, -1):  # От 5 месяцев назад до текущего месяца
                # Вычисляем начало и конец месяца
                if i == 0:
                    # Текущий месяц
                    year = current_date.year
                    month = current_date.month
                else:
                    # Предыдущие месяцы
                    month = current_date.month - i
                    year = current_date.year
                    while month <= 0:
                        month += 12
                        year -= 1
                
                month_start = datetime(year, month, 1)
                if month == 12:
                    month_end = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    month_end = datetime(year, month + 1, 1) - timedelta(days=1)
                
                cursor.execute("""
                    SELECT COALESCE(SUM(Amount), 0)
                    FROM Donations 
                    WHERE EXTRACT(YEAR FROM DonationDate) = %s
                      AND EXTRACT(MONTH FROM DonationDate) = %s
                """, [year, month])
                row = cursor.fetchone()
                total = float(row[0]) if row[0] else 0.0
                
                month_name = month_names[month - 1]
                donations_by_month.append({
                    'month': month_name,
                    'total': total,
                })
            
            stats['donations_by_month'] = donations_by_month
        
        return stats


class StatisticsPDFView(AdminOrManagerRequiredMixin, View):
    """Генерация PDF отчета со статистикой - улучшенный дизайн"""
    def get(self, request):
        user_id = get_user_id_from_jwt(request)
        if not user_id:
            return HttpResponse('Необходима авторизация', status=403)
        if not HAS_REPORTLAB:
            return HttpResponse('PDF генерация недоступна (требуется reportlab). Установите: pip install reportlab', status=503)

        stats_view = StatisticsView()
        stats = stats_view._get_statistics()

        import os
        import platform
        import tempfile

        # Выбираем шрифт с кириллицей (лучше Arial на Windows)
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

        primary_color = colors.HexColor('#F08A24')  # основной (оранжевый)
        secondary_color = colors.HexColor('#004E89')  # контраст (синий)
        muted_text = colors.HexColor('#6C757D')
        dark_text = colors.HexColor('#212529')
        light_bg = colors.HexColor('#F8F9FA')
        border_color = colors.HexColor('#E5E0DB')

        page_w, page_h = A4
        left_margin = 50
        right_margin = 50
        top_margin = 90
        bottom_margin = 50
        usable_w = page_w - left_margin - right_margin

        def on_page(canvas, _doc):
            canvas.saveState()
            bar_height = 24
            bar_y = page_h - 60

            # Плашка во всю ширину
            canvas.setFillColor(primary_color)
            canvas.roundRect(left_margin, bar_y, usable_w, bar_height, 8, fill=1, stroke=0)

            # Логотип-иконка слева (квадрат + лапа) ровно по центру плашки
            icon_size = 10
            icon_x = left_margin + 14
            icon_y = bar_y + bar_height / 2

            canvas.setFillColor(colors.white)
            canvas.roundRect(icon_x - icon_size / 2, icon_y - icon_size / 2, icon_size, icon_size, 2, fill=1, stroke=0)
            canvas.setFillColor(primary_color)
            canvas.setFont(font_name, 8)
            canvas.drawCentredString(icon_x, icon_y - 3, "🐾")

            # Текст заголовка
            canvas.setFillColor(colors.white)
            canvas.setFont(font_name, 11)
            canvas.drawString(icon_x + icon_size + 6, bar_y + 7, "Анималити • Статистика")

            # Дата справа, выровненная по центру по вертикали
            canvas.setFillColor(muted_text)
            canvas.setFont(font_name, 9)
            canvas.drawRightString(left_margin + usable_w - 10, icon_y - 3, timezone.now().strftime("%d.%m.%Y %H:%M"))

            canvas.restoreState()

        # PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )
        story = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'PdfTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=20,
            textColor=secondary_color,
            alignment=TA_LEFT,
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            'PdfSubtitle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            textColor=muted_text,
            alignment=TA_LEFT,
            spaceAfter=10,
        )
        section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=12,
            textColor=secondary_color,
            alignment=TA_LEFT,
            spaceAfter=6,
        )
        label_style = ParagraphStyle(
            'LabelSmall',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=9,
            textColor=muted_text,
        )
        value_style = ParagraphStyle(
            'ValueSmall',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            textColor=dark_text,
        )

        # Заголовок
        story.append(Spacer(1, 6))
        story.append(Paragraph('ОТЧЕТ ПО СТАТИСТИКЕ ПРИЮТА', title_style))
        story.append(Paragraph('Анималити • сводка по ключевым показателям', subtitle_style))

        # Карточка "метрика"
        def stat_card(title, value, color):
            cell = Table(
                [
                    [Paragraph(f"<b>{title}</b>", label_style)],
                    [Paragraph(f"<font size='14' color='{color}'><b>{value}</b></font>", value_style)],
                ],
                colWidths=[usable_w / 2 - 14],
            )
            cell.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('BOX', (0, 0), (-1, -1), 0.6, border_color),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('LINEBELOW', (0, 1), (-1, 1), 3, color),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ]))
            return cell

        key = [
            ('Всего животных', str(stats['animals']['total']), colors.HexColor('#1A659E')),
            ('Всего пользователей', str(stats['users']['total']), colors.HexColor('#06A77D')),
            ('Всего заявок', str(stats['applications']['total']), colors.HexColor('#E63946')),
            ('Пожертвований', f"{stats['donations']['total_amount']:,.0f} ₽", colors.HexColor('#F7B801')),
        ]

        card_grid = Table(
            [
                [stat_card(key[0][0], key[0][1], key[0][2]), stat_card(key[1][0], key[1][1], key[1][2])],
                [stat_card(key[2][0], key[2][1], key[2][2]), stat_card(key[3][0], key[3][1], key[3][2])],
            ],
            colWidths=[usable_w / 2 - 7, usable_w / 2 - 7],
        )
        card_grid.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(Spacer(1, 8))
        story.append(card_grid)

        # Сводка блоками (2 колонки)
        def summary_block(title, color, items):
            data = [[Paragraph(f"<b>{title}</b>", ParagraphStyle('BlkTitle', parent=section_title_style, textColor=colors.white))]]
            # Заголовок блока
            block_title = Table([[Paragraph(f"<b>{title}</b>", ParagraphStyle('BlkTitle2', parent=styles['Heading2'], fontName=font_name, fontSize=11, textColor=colors.white, alignment=TA_LEFT))]],
                                colWidths=[usable_w / 2 - 14])
            block_title.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), color),
                ('BOX', (0, 0), (-1, -1), 0.6, color),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))

            rows = []
            for lbl, val in items:
                rows.append([Paragraph(lbl, label_style), Paragraph(f"<b>{val}</b>", value_style)])
            # Две колонки фиксированной пропорции, чтобы все блоки были одинаковой ширины
            col_label = (usable_w / 2 - 14) * 0.6
            col_value = (usable_w / 2 - 14) * 0.4
            tbl = Table(rows, colWidths=[col_label, col_value])
            tbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), light_bg),
                ('BOX', (0, 0), (-1, -1), 0.6, border_color),
                ('GRID', (0, 0), (-1, -1), 0.2, border_color),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            return Table([[block_title], [tbl]], colWidths=[usable_w / 2 - 14])

        # Чтобы блоки не выглядели “ломаными”, делаем простую верстку 2x3
        # (используем Table с 2 колонками на строку)
        left_block = summary_block(
            'ЖИВОТНЫЕ', colors.HexColor('#1A659E'),
            [
                ('Всего', stats['animals']['total']),
                ('Доступно', stats['animals']['available']),
                ('Недоступно', stats['animals']['not_available']),
            ],
        )
        right_block = summary_block(
            'ПОЛЬЗОВАТЕЛИ', colors.HexColor('#06A77D'),
            [
                ('Всего', stats['users']['total']),
                ('Гости', stats['users']['guests']),
                ('Менеджеры', stats['users']['managers']),
                ('Админы', stats['users']['admins']),
            ],
        )
        story.append(Spacer(1, 14))
        summary_grid1 = Table([[left_block, right_block]], colWidths=[usable_w / 2 - 7, usable_w / 2 - 7])
        summary_grid1.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        story.append(summary_grid1)

        story.append(Spacer(1, 12))
        story.append(Paragraph('Детализация', section_title_style))
        # Ряд 2
        story.append(
            Table(
                [[
                    summary_block(
                        'ЗАЯВКИ', colors.HexColor('#E63946'),
                        [
                            ('Всего', stats['applications']['total']),
                            ('Одобрено', stats['applications']['approved']),
                            ('В ожидании', stats['applications']['pending']),
                            ('Отклонено', stats['applications'].get('rejected', 0)),
                        ],
                    ),
                    summary_block(
                        'ПОЖЕРТВОВАНИЯ', colors.HexColor('#F7B801'),
                        [
                            ('Всего', stats['donations']['total']),
                            ('Сумма', f"{stats['donations']['total_amount']:,.2f} ₽".replace(',', ' ')),
                            ('Средняя', f"{stats['donations']['avg_amount']:,.2f} ₽".replace(',', ' ')),
                            ('Макс.', f"{stats['donations']['max_amount']:,.2f} ₽".replace(',', ' ')),
                        ],
                    )
                ]],
                colWidths=[usable_w / 2 - 7, usable_w / 2 - 7],
            )
        )
        story.append(Spacer(1, 12))

        # Ряд 3
        story.append(
            Table(
                [[
                    summary_block(
                        'НОВОСТИ', colors.HexColor('#7209B7'),
                        [
                            ('Всего', stats['news']['total']),
                            ('Опубликовано', stats['news']['published']),
                            ('Не опубликовано', stats['news']['unpublished']),
                        ],
                    ),
                    summary_block(
                        'АКТИВНОСТЬ (30 ДНЕЙ)', colors.HexColor('#F08A24'),
                        [
                            ('Пользователи', stats['new_users_30_days']),
                            ('Заявки', stats['new_applications_30_days']),
                            ('Пожертвования', stats['donations_30_days']['count']),
                        ],
                    )
                ]],
                colWidths=[usable_w / 2 - 7, usable_w / 2 - 7],
            )
        )

        # Диаграммы
        story.append(PageBreak())

        if HAS_MATPLOTLIB:
            import matplotlib.pyplot as plt

            def chart_path(name: str) -> str:
                return os.path.join(tempfile.gettempdir(), f"{name}_{timezone.now().timestamp()}.png")

            def create_chart_image(chart_type, stats_data, path):
                plt.style.use('seaborn-v0_8-darkgrid' if 'seaborn-v0_8-darkgrid' in plt.style.available else 'default')
                plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans', 'sans-serif']
                plt.rcParams['axes.unicode_minus'] = False

                if chart_type == 'status_pie':
                    fig, ax = plt.subplots(figsize=(7.5, 4.8), facecolor='white')
                    items = [s for s in stats_data['animal_statuses'] if s['count'] > 0]
                    labels = [i['name'] for i in items]
                    sizes = [i['count'] for i in items]
                    colors_list = ['#1A659E', '#06A77D', '#F7B801', '#E63946', '#7209B7', '#004E89']
                    ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors_list[:len(sizes)], startangle=90,
                           textprops={'fontsize': 9, 'fontweight': 'bold'})
                    ax.set_title('Статусы животных', fontsize=14, fontweight='bold', color=dark_text, pad=14)
                    plt.tight_layout()

                elif chart_type == 'type_pie':
                    fig, ax = plt.subplots(figsize=(7.5, 4.8), facecolor='white')
                    items = [t for t in stats_data['animal_types'] if t['count'] > 0]
                    labels = [i['name'] for i in items]
                    sizes = [i['count'] for i in items]
                    colors_list = ['#1A659E', '#06A77D', '#F7B801', '#E63946', '#7209B7']
                    ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors_list[:len(sizes)], startangle=90,
                           textprops={'fontsize': 9, 'fontweight': 'bold'})
                    ax.set_title('Типы животных (ТОП-5)', fontsize=14, fontweight='bold', color=dark_text, pad=14)
                    plt.tight_layout()

                elif chart_type == 'donations_bar':
                    fig, ax = plt.subplots(figsize=(7.5, 4.8), facecolor='white')
                    months = [m['month'] for m in stats_data['donations_by_month']]
                    amounts = [m['total'] for m in stats_data['donations_by_month']]
                    bars = ax.bar(months, amounts, color=secondary_color, alpha=0.85, edgecolor=primary_color, linewidth=1.2)
                    for bar in bars:
                        h = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width() / 2, h, f"{int(h):,}".replace(',', ' '),
                                ha='center', va='bottom', fontsize=8, fontweight='bold', color=dark_text)
                    ax.set_title('Пожертвования за 6 месяцев', fontsize=14, fontweight='bold', color=dark_text, pad=14)
                    ax.set_ylabel('Сумма (₽)', fontsize=10, fontweight='bold')
                    ax.grid(axis='y', alpha=0.25, linestyle='--')
                    plt.xticks(rotation=35, ha='right')
                    plt.tight_layout()

                elif chart_type == 'applications_bar':
                    fig, ax = plt.subplots(figsize=(7.5, 4.8), facecolor='white')
                    categories = ['Одобрено', 'В ожидании', 'Отклонено']
                    values = [
                        stats_data['applications']['approved'],
                        stats_data['applications']['pending'],
                        stats_data['applications'].get('rejected', 0),
                    ]
                    colors_bar = ['#06A77D', '#F7B801', '#E63946']
                    bars = ax.bar(categories, values, color=colors_bar, alpha=0.9)
                    for bar in bars:
                        h = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width() / 2, h, f"{int(h)}",
                                ha='center', va='bottom', fontsize=10, fontweight='bold', color=dark_text)
                    ax.set_title('Заявки: статусная динамика', fontsize=14, fontweight='bold', color=dark_text, pad=14)
                    ax.set_ylabel('Количество', fontsize=10, fontweight='bold')
                    ax.grid(axis='y', alpha=0.25, linestyle='--')
                    plt.tight_layout()

                plt.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
                plt.close()

            paths = {
                'status': chart_path('status'),
                'type': chart_path('type'),
                'donations': chart_path('donations'),
                'applications': chart_path('applications'),
            }

            try:
                create_chart_image('status_pie', stats, paths['status'])
                create_chart_image('type_pie', stats, paths['type'])
                create_chart_image('donations_bar', stats, paths['donations'])
                create_chart_image('applications_bar', stats, paths['applications'])

                story.append(Spacer(1, 10))
                story.append(Paragraph('ВИЗУАЛИЗАЦИЯ ДАННЫХ', section_title_style))
                story.append(Spacer(1, 8))

                def img_with_caption(img_path, caption):
                    img = Image(img_path, width=usable_w / 2 - 20, height=2.6 * inch)
                    cap = Paragraph(caption, ParagraphStyle('Cap', parent=styles['Normal'], fontName=font_name, fontSize=9, textColor=muted_text, alignment=TA_CENTER))
                    box = Table([[img], [cap]], colWidths=[usable_w / 2 - 20])
                    box.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
                    return box

                row1 = Table(
                    [[
                        img_with_caption(paths['status'], 'Статусы'),
                        img_with_caption(paths['type'], 'Типы'),
                    ]],
                    colWidths=[usable_w / 2, usable_w / 2],
                )
                row2 = Table(
                    [[
                        img_with_caption(paths['donations'], 'Пожертвования'),
                        img_with_caption(paths['applications'], 'Заявки'),
                    ]],
                    colWidths=[usable_w / 2, usable_w / 2],
                )
                row1.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
                row2.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
                story.append(row1)
                story.append(Spacer(1, 10))
                story.append(row2)

            finally:
                for p in paths.values():
                    try:
                        if os.path.exists(p):
                            os.remove(p)
                    except Exception:
                        pass

        # Собираем PDF
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        filename = f'statistics_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class StatisticsCSVView(AdminOrManagerRequiredMixin, View):
    """Генерация CSV отчета со статистикой - улучшенный формат"""
    def get(self, request):
        user_id = get_user_id_from_jwt(request)
        if not user_id:
            return HttpResponse('Необходима авторизация', status=403)
        
        # Получаем статистику
        stats_view = StatisticsView()
        stats = stats_view._get_statistics()
        
        # Создаем CSV с улучшенным форматированием
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        filename = f'statistics_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Пишем CSV с поддержкой кириллицы и красивым форматированием
        writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        # Функция для создания разделителя (в двух столбцах)
        def write_separator():
            writer.writerow(['=' * 40, '=' * 40])
        
        # Функция для создания заголовка секции
        def write_section_header(title):
            writer.writerow(['', ''])  # Пустая строка
            writer.writerow([title.upper(), ''])
            writer.writerow(['-' * 40, '-' * 40])
        
        # Функция для создания подзаголовка
        def write_subsection_header(title):
            writer.writerow(['', ''])  # Пустая строка
            writer.writerow([title, ''])
        
        # Заголовок отчета (без эмодзи, чтобы в Excel всё выглядело аккуратно)
        writer.writerow(['ОТЧЕТ ПО СТАТИСТИКЕ ПРИЮТА', ''])
        writer.writerow(['Анималити', ''])
        writer.writerow(['', ''])
        writer.writerow(['Дата формирования:', timezone.now().strftime("%d.%m.%Y %H:%M")])
        writer.writerow(['', ''])
        write_separator()
        writer.writerow(['', ''])
        
        # ЖИВОТНЫЕ
        write_section_header('ЖИВОТНЫЕ')
        writer.writerow(['Показатель', 'Значение'])
        writer.writerow(['Всего животных', stats['animals']['total']])
        writer.writerow(['Доступно для усыновления', stats['animals']['available']])
        writer.writerow(['Недоступно', stats['animals']['not_available']])
        
        # Статусы животных
        write_subsection_header('Статусы животных')
        writer.writerow(['Статус', 'Количество'])
        for status in stats['animal_statuses']:
            writer.writerow([status['name'], status['count']])
        
        # Типы животных
        write_subsection_header('Типы животных (топ-5)')
        writer.writerow(['Тип', 'Количество'])
        for type_item in stats['animal_types']:
            writer.writerow([type_item['name'], type_item['count']])
        
        # ПОЛЬЗОВАТЕЛИ
        write_section_header('ПОЛЬЗОВАТЕЛИ')
        writer.writerow(['Показатель', 'Значение'])
        writer.writerow(['Всего пользователей', stats['users']['total']])
        writer.writerow(['Гости', stats['users']['guests']])
        writer.writerow(['Менеджеры', stats['users']['managers']])
        writer.writerow(['Администраторы', stats['users']['admins']])
        
        # ЗАЯВКИ НА УСЫНОВЛЕНИЕ
        write_section_header('ЗАЯВКИ НА УСЫНОВЛЕНИЕ')
        writer.writerow(['Показатель', 'Значение'])
        writer.writerow(['Всего заявок', stats['applications']['total']])
        writer.writerow(['Одобрено', stats['applications']['approved']])
        writer.writerow(['В ожидании', stats['applications']['pending']])
        writer.writerow(['Отклонено', stats['applications'].get('rejected', 0)])
        
        # ПОЖЕРТВОВАНИЯ
        write_section_header('ПОЖЕРТВОВАНИЯ')
        writer.writerow(['Показатель', 'Значение'])
        writer.writerow(['Всего пожертвований', stats['donations']['total']])
        writer.writerow(['Общая сумма (₽)', f"{stats['donations']['total_amount']:,.2f}"])
        writer.writerow(['Средняя сумма (₽)', f"{stats['donations']['avg_amount']:,.2f}"])
        writer.writerow(['Максимальная сумма (₽)', f"{stats['donations']['max_amount']:,.2f}"])
        
        # Пожертвования по месяцам
        write_subsection_header('Пожертвования по месяцам (последние 6 месяцев)')
        writer.writerow(['Месяц', 'Сумма (₽)'])
        for month in stats['donations_by_month']:
            writer.writerow([month['month'], f"{month['total']:,.2f}"])
        
        # НОВОСТИ
        write_section_header('НОВОСТИ')
        writer.writerow(['Показатель', 'Значение'])
        writer.writerow(['Всего новостей', stats['news']['total']])
        writer.writerow(['Опубликовано', stats['news']['published']])
        writer.writerow(['Не опубликовано', stats['news']['unpublished']])
        
        # АКТИВНОСТЬ ЗА ПОСЛЕДНИЕ 30 ДНЕЙ
        write_section_header('АКТИВНОСТЬ ЗА ПОСЛЕДНИЕ 30 ДНЕЙ')
        writer.writerow(['Показатель', 'Значение'])
        writer.writerow(['Новых пользователей', stats['new_users_30_days']])
        writer.writerow(['Новых заявок', stats['new_applications_30_days']])
        writer.writerow(['Встреч', stats['meetings_30_days']])
        writer.writerow(['Пожертвований', stats['donations_30_days']['count']])
        writer.writerow(['Сумма пожертвований (₽)', f"{stats['donations_30_days']['total']:,.2f}"])
        
        # Конец отчета
        writer.writerow(['', ''])
        write_separator()
        writer.writerow(['', ''])
        writer.writerow(['Конец отчета', ''])
        writer.writerow(['', ''])
        write_separator()
        
        return response

