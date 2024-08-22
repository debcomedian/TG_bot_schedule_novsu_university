import pandas as pd
import tempfile
from code.db import Database

days_full = ['ПОНЕДЕЛЬНИК', 'ВТОРНИК', 'СРЕДА', 'ЧЕТВЕРГ', 'ПЯТНИЦА', 'СУББОТА']

def init_get_df(content):
    with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
        tmp_file.write(content)
        tmp_file.seek(0)
        df = pd.read_excel(tmp_file)
    return df

def init_find_distance(group_student, day_of_week, df):
    #Найти индекс столбца, содержащего дни недели
    col_index = next((col for col in df.columns if any(day in df[col].values for day in days_full)), None)
    if col_index is not None:
        # Найти индексы строк, содержащих дни недели
        days_of_week = {'ПН': 'ПОНЕДЕЛЬНИК', 'ВТ': 'ВТОРНИК', 'СР': 'СРЕДА',
                        'ЧТ': 'ЧЕТВЕРГ', 'ПТ': 'ПЯТНИЦА', 'СБ': 'СУББОТА'}
        day_indices = {day: [] for day in days_of_week.values()}
        
        for index, value in enumerate(df[col_index]):
            if value in days_of_week.values():
                day_indices[value].append(index)

        if day_of_week.upper() in days_of_week:
            current_day = days_of_week[day_of_week.upper()]
            next_day = days_of_week.get(init_get_next_weekday(day_of_week.upper()), None)

            if next_day is not None:
                if len(day_indices[current_day]) > 0 and len(day_indices[next_day]) > 0:
                    distance = day_indices[next_day][0] - day_indices[current_day][-1]
                    return distance
    return 0

def init_get_next_weekday(days):
    days_of_week = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ']
    current_day_index = days_of_week.index(days)
    return days_of_week[(current_day_index + 1) % len(days_of_week)]

def init_schedule_ptk(group_student, day_of_week, content):
    df = init_get_df(content)
    day_of_week_values = {'Пн': 'ПОНЕДЕЛЬНИК', 'Вт': 'ВТОРНИК', 'Ср': 'СРЕДА',
                          'Чт': 'ЧЕТВЕРГ', 'Пт': 'ПЯТНИЦА', 'Сб': 'СУББОТА'}
    row_index = None
    for row_idx, row in df.iterrows():
        for col_idx, cell in enumerate(row):
            if cell == day_of_week_values.get(day_of_week):
                row_index = row_idx
                break
        if row_index is not None:
            break

    column_index = None
    for column_index, column_name in enumerate(df.columns):
        if group_student in df[column_name].values:
            break

    schedule = []
    #print(f'group_student --> {group_student}\nday_os_week --> {day_of_week}\n')
    for i in range(init_find_distance(group_student, day_of_week, df)):
        time = df.iloc[row_index + i, column_index - 1]
        info = df.iloc[row_index + i, column_index]
        timeN = df.iloc[row_index + i - 1, column_index - 1]
        info = remove_lek_from_info(info)
        #print(info)
        # Обычная неделя без верха низа:

        if pd.notna(time) and pd.notna(info):
            # Предмет без групп
            if len(info.split(', ')) == 3:
                subject, teacher, audience = info.split(', ')
                schedule.append(
                    f' ⏰Время: {time} \n 📚Предмет: {subject} \n 👨‍🏫Преподаватель: {teacher} \n 📝Аудитория: {audience}\n\n')
            # Предмет по группам:
            elif len(info.split(', ')) == 5:
                subject, teacher1, audience1, teacher2, audience2 = info.split(', ')
                if pd.notna(time) and pd.notna(info):
                    schedule.append(
                        f' 📚Предмет: {subject} \n'
                        f' Группа 1: \n ⏰Время: {time} \n 👨‍🏫Преподаватель: {teacher1} \n 📝Аудитория: {audience1} \n\n' +
                        f' Группа 2: \n ⏰Время: {time} \n 👨‍🏫Преподаватель: {teacher2} \n 📝Аудитория: {audience2} \n\n')
    
        # Если появляется верхний нижний предмет:

        elif pd.isna(time) and pd.notna(info):
            # Предмет без групп нижней недели:
            if len(info.split(', ')) == 3:
                subject, teacher, audience = info.split(', ')
                schedule.append(
                    f' ⏰Время: {timeN} \n Предмет: {subject} \n Преподаватель: {teacher} \n Аудитория: {audience} - только по нижней неделе \n\n')
            # Предмет по группам нижней недели:
            elif len(info.split(', ')) == 5:
                subject1, teacher1, audience1, subject2, teacher2, audience2 = info.split(', ')
                if pd.notna(time) and pd.notna(info):
                    schedule.append(
                        f' Группа 1: \n ⏰Время: {time} \n 📚Предмет: {subject1} \n 👨‍🏫Преподаватель: {teacher1} \n 📝Аудитория: {audience1} - только по нижней неделе \n\n' +
                        f' Группа 2: \n ⏰Время: {time} \n 📚Предмет: {subject2} \n 👨‍🏫Преподаватель: {teacher2} \n 📝Аудитория: {audience2} - только по нижней неделе \n\n')
                    
    return schedule

def remove_lek_from_info(info):
    if isinstance(info, str) and ',' in info:
        parts = info.split(', ')
        if len(parts) > 3:
            return ', '.join(parts[:3])
    return info

def init_send_schedule(schedule, number_group, day, week_type):
    for i, elem in enumerate(schedule):
        if ' - только по нижней неделе' in elem:
            schedule[i - 1] = schedule[i - 1].rstrip('\n\n')
            schedule[i - 1] += ' - только по верхней неделе \n\n'

    for i, elem in enumerate(schedule):
        if week_type == 'Верхняя':
            if ' - только по нижней неделе' in elem:
                del schedule[i]
        elif week_type == 'Нижняя':
            if ' - только по верхней неделе' in elem:
                del schedule[i]
    query = f'INSERT INTO group_{number_group} (week_day, group_week_type, group_data) VALUES (%s, %s, %s)'
    params = (day, week_type == "Верхняя", ''.join(schedule))
    Database.execute_query(query, params)

def get_schedule_ptk(group_student, day_of_week, week_type):
    query = f'SELECT group_data FROM group_{group_student} WHERE week_day=%s AND group_week_type=%s'
    schedule = Database.execute_query(query, (day_of_week, week_type == "Верхняя"), fetch=True)
    schedule = [' '.join(map(str, item)) if isinstance(item, tuple) else str(item) for item in schedule]
    return '\n'.join(schedule)
