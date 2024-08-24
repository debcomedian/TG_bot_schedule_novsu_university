import pandas as pd
import requests

from bs4 import BeautifulSoup as BS
from transliterate import translit


from code.db import Database

days_full = ['ПОНЕДЕЛЬНИК', 'ВТОРНИК', 'СРЕДА', 'ЧЕТВЕРГ', 'ПЯТНИЦА', 'СУББОТА']

def get_schedule_ptk(group_student, day_of_week, week_type):
    query = f'SELECT group_data FROM group_{group_student} WHERE week_day=%s AND group_week_type=%s'
    schedule = Database.execute_query(query, (day_of_week, week_type == "Верхняя"), fetch=True)
    schedule = [' '.join(map(str, item)) if isinstance(item, tuple) else str(item) for item in schedule]
    return schedule

def parse_institutes_data(data):
    parsed_data = []

    courses = data.split('|')
    for course_data in courses:
        course_data = course_data.replace('Группы:', '').strip()
        course_parts = course_data.split(',')
        if len(course_parts) > 1:  # Проверяем, есть ли данные после разделителя
            course_info = course_parts[0].split(':')
            if len(course_info) > 1:  # Проверяем, есть ли разделитель ":"
                course_number = course_info[1].strip()
                groups = course_parts[1:]
                for group_id in groups:
                    group_id = group_id.strip()
                    if len(group_id) >= 4:
                        link = group_id.split('(', 1)[-1].strip(')').strip()
                        group_id = group_id.split('(')[0].strip()
                        parsed_data.append((int(course_number.split()[0]), group_id, link))
            else:
                print("Неверный формат курса:", course_parts[0])
        else:
            print("Неверный формат данных:", course_data)

    return parsed_data


def init_list_group(institude, data):
    parsed_data = parse_institutes_data(data)
    
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS groups_students_{institude} (
        group_course SMALLINT NOT NULL, 
        group_id VARCHAR(6) NOT NULL,
        link VARCHAR(116) NOT NULL
    )
    """
    Database.execute_query(create_table_query)

    # Вставка данных
    for course_number, group_id, link in parsed_data:
        insert_query = f"""
        INSERT INTO groups_students_{institude} 
        (group_course, group_id, link) 
        VALUES (%s, %s, %s)
        """
        Database.execute_query(insert_query, (course_number, group_id, link))



def init_list_groups(soup):
    tables = soup.find_all('table', class_='viewtable')

    institutes = {}
    current_institute = None
    current_data = []
    institute_names = []
    
    for table in tables:
        th = table.find('th')
        if th:
            if current_institute:
                institutes[current_institute] = '| '.join(current_data)
            current_institute = translit(th.text.strip(), 'ru', reversed=True).lower()
            current_data = []
        else:
            trs = table.find_all('tr')
            headers = [td.text.strip() for td in trs[0].find_all('td')]

            for tr in trs[1:]:
                tds = tr.find_all('td')
                if len(tds) == len(headers):
                    for header, td in zip(headers, tds):
                        links = td.find_all('a')
                        groups_with_links = []
                        for link in links:
                            group_name = link.text.strip().replace('\t', '').replace('\n', '\^').replace(' ', '').strip()
                            group_link = link.get('href', '').strip()
                            if 'instId' in group_link:
                                inst_id_start = group_link.find('&')
                                group_link = group_link[inst_id_start:]
                            if group_name and group_link:
                                groups_with_links.append(f'{group_name}({group_link})')

                        if groups_with_links:
                            group = ', '.join(groups_with_links)
                            current_data.append(f'Курс: {header}, Группы: {group}')

    if current_institute:
        institutes[current_institute] = '| '.join(current_data)

    for institute, data in list(institutes.items()):
        if not any(char.isdigit() for char in institute):
            init_list_group(institute, data)
            institute_names.append(institute)
        else:
            del institutes[institute]
    
    return institute_names

def format_time_range(time_string):
    time_parts = []
    part = ""
    
    i = 0
    while i < len(time_string):
        char = time_string[i]
        part += char

        # Определяем, нужно ли добавить этот отрезок времени в список
        if len(part) == 5:
            time_parts.append(part)
            part = ""
        elif len(part) == 4 and int(part[0]) > 2:  # Если первая цифра больше 2, значит, это некорректное время
            time_parts.append(part)
            part = ""

        i += 1

    if len(time_parts) > 1:
        return f"{time_parts[0]}-{time_parts[-1]}"
    elif len(time_parts) == 1:
        return time_parts[0]
    else:
        return "Нет данных"

def parse_schedule_entry(entry, previous_entry=None):
    if previous_entry and len(entry) > 0 and not entry[0]:
        # Используем предыдущее время, если текущее время пустое
        time = previous_entry["time"]
        subgroup = entry[0] if len(entry) > 0 else previous_entry["subgroup"]
        subject = entry[1] if len(entry) > 1 else previous_entry["subject"]
        teacher = entry[2] if len(entry) > 2 else previous_entry["teacher"]
        room = entry[3] if len(entry) > 3 else previous_entry["room"]
        comments = entry[4] if len(entry) > 4 else previous_entry["comments"]
    else:
        time = format_time_range(entry[0]) if len(entry) > 0 and entry[0] else "Нет данных"
        subgroup = entry[1] if len(entry) > 1 else ""
        subject = entry[2] if len(entry) > 2 else ""
        teacher = entry[3] if len(entry) > 3 else ""
        room = entry[4] if len(entry) > 4 else ""
        comments = entry[5] if len(entry) > 5 else ""

    return {
        "time": time,
        "subgroup": subgroup,
        "subject": subject,
        "teacher": teacher,
        "room": room,
        "comments": comments
    }

def print_schedule(schedule):
    for day, entries in schedule.items():
        print(f'Расписание на {day}:')
        seen_entries = set()
        previous_entry = None

        for entry in entries:
            entry_dict = parse_schedule_entry(entry, previous_entry)
            entry_tuple = tuple(entry_dict.values())

            if entry_tuple in seen_entries:
                continue
            seen_entries.add(entry_tuple)

            previous_entry = entry_dict  # Сохраняем текущую запись для следующей итерации

            # Печать информации
            print('Время:', entry_dict["time"] if entry_dict["time"] else "Нет данных")
            print('Подгруппа:', entry_dict["subgroup"])
            print('Предмет:', entry_dict["subject"])
            print('Преподаватель:', entry_dict["teacher"])
            print('Аудитория:', entry_dict["room"])
            print('Комментарии:', entry_dict["comments"])
            print('---')

        print('\n' + '='*40 + '\n')

def parse_week_type(comments):
    if "верх." in comments.lower():
        return 1
    elif "нижн." in comments.lower():
        return 0
    return None

def format_schedule_entry(entry_dict):
    return (
        f"⏰Время: {entry_dict['time']}\n"
        f"📚Предмет: {entry_dict['subject']}\n"
        f"👨‍🏫Преподаватель: {entry_dict['teacher']}\n"
        f"📝Аудитория: {entry_dict['room']}\n"
        f"📝Комментарий: {entry_dict['comments']}\n"
    )

def save_schedule_to_db(group, schedule):
    for day, entries in schedule.items():
        seen_entries = set()
        previous_entry = None
        day_schedule_upper = []
        day_schedule_lower = []

        for entry in entries:
            entry_dict = parse_schedule_entry(entry, previous_entry)
            entry_tuple = tuple(entry_dict.values())

            if entry_tuple in seen_entries:
                continue
            seen_entries.add(entry_tuple)

            previous_entry = entry_dict  # Сохраняем текущую запись для следующей итерации

            # Формируем данные для сохранения
            formatted_entry = format_schedule_entry(entry_dict)

            # Определяем тип недели и распределяем записи по верхней или нижней неделе
            week_type = parse_week_type(entry_dict['comments'])
            if week_type == 1:  # Верхняя неделя
                day_schedule_upper.append(formatted_entry)
            elif week_type == 0:  # Нижняя неделя
                day_schedule_lower.append(formatted_entry)
            else:  # Если неделя не указана, сохраняем в обе недели
                day_schedule_upper.append(formatted_entry)
                day_schedule_lower.append(formatted_entry)

        # Сохраняем расписание для верхней недели
        if day_schedule_upper:
            upper_schedule_str = "\n".join(day_schedule_upper)
            insert_query = f"""
            INSERT INTO group_{group} 
            (week_day, group_week_type, group_data) 
            VALUES (%s, %s, %s)
            """
            params = (day, True, upper_schedule_str)
            Database.execute_query(insert_query, params)

        # Сохраняем расписание для нижней недели
        if day_schedule_lower:
            lower_schedule_str = "\n".join(day_schedule_lower)
            insert_query = f"""
            INSERT INTO group_{group} 
            (week_day, group_week_type, group_data) 
            VALUES (%s, %s, %s)
            """
            params = (day, False, lower_schedule_str)
            Database.execute_query(insert_query, params)

def get_group_link(institute, group):
    
    link = "https://portal.novsu.ru/univer/timetable/ochn/i.1103357/?page=EditViewGroup&instId="
    
    result = Database.execute_query(f"SELECT link from groups_students_{institute} WHERE group_id = '{group}'", fetch=True)

    if result:
        link += result[0][0]
    else:
        print(f"No link found for group_id {group} in institute {institute}")

    return link

def init_schedule(soup, institute, groups):
    for group in groups:
        Database.rebuild_group_table(group)
        
        link = get_group_link(institute, group)
        response = requests.get(link)
        html = response.text
        soup = BS(html, 'html.parser')
        table = soup.find('table', {'class': 'shedultable'})

        if table is None:
            print("Таблица не найдена на странице.")
            continue
        
        schedule = {}
        current_day = None

        for row in table.find_all('tr'):
            row_data = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]

            if row_data[0] in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']:
                # Новый день недели
                current_day = row_data[0]
                if current_day not in schedule:
                    schedule[current_day] = []
                if len(row_data) > 1:  # Если в строке есть и дата, и данные расписания
                    schedule[current_day].append(row_data[1:])
            else:
                # Это продолжение расписания для текущего дня
                if current_day:
                    schedule[current_day].append(row_data)

        save_schedule_to_db(group, schedule)
