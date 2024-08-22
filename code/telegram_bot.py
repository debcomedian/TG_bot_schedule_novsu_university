import telebot
import time
import threading
import requests

from telebot import types
from bs4 import BeautifulSoup as BS
from datetime import datetime, timedelta

from code.db import Database
from code.menu_handler import *
from code.config import get_telegram_token
from code.schedule import init_schedule_ptk, get_schedule_ptk, init_send_schedule

STATE_MAIN_MENU = 'main_menu'
STATE_SELECTING_LOCATION = 'selecting_location'
STATE_SELECTING_SCHEDULE = 'selecting_schedule'
STATE_SELECTING_COURSE = 'selecting_course'
STATE_SELECTING_GROUP = 'selecting_group'
STATE_SELECTING_WEEK_TYPE = 'selecting_week_type'
STATE_SELECTING_DAY = 'selecting_day'
STATE_SETTINGS_SELECTING_COLLEGE = 'settings_selecting_college'
STATE_SETTINGS_SELECTING_COURSE = 'settings_selecting_course'
STATE_SETTINGS_SELECTING_GROUP = 'settings_selecting_group'
STATE_SETTINGS_SELECTING_TIME = 'settings_selecting_time'

bot = telebot.TeleBot(get_telegram_token())
update_lock = threading.Lock()

days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']

user_context = {}
group = []

def init_list_group(first_group_number, college, list_group):
    course = 1
    for num_group in list_group:
        temp = int(num_group) // 1000
        if (first_group_number != temp):
            course += 1
            first_group_number = temp

        Database.execute_query(f"INSERT INTO groups_students_{college} (group_course, group_id) VALUES (%s, %s)"
                               , (course, num_group))


def init_list_groups(soup):
    substring_ptk = "/npe/files/_timetable/ptk/"
    substring_pedcol = "/npe/files/_timetable/pedcol/"
    substring_medcol = "/npe/files/_timetable/medcol/"
    substring_spour = "/npe/files/_timetable/spour/"
    substring_spoinpo = "/npe/files/_timetable/spoinpo/"
    
    list_group_ptk, list_group_pedcol, list_group_medcol = [], [], []
    list_group_spour, list_group_spoinpo = [], []
    
    list_groups = soup.find_all('a')
    for element in list_groups:
        if substring_ptk in str(element) and '_' not in element.get_text(): 
            list_group_ptk.append(element.get_text())
        elif substring_pedcol in str(element) and '_' not in element.get_text():
            list_group_pedcol.append(element.get_text())
        elif substring_medcol in str(element) and '_' not in element.get_text():
            list_group_medcol.append(element.get_text())
        elif substring_spour in str(element) and '_' not in element.get_text():
            list_group_spour.append(element.get_text())
        elif substring_spoinpo in str(element) and ('_' and 'o' not in element.get_text()):
            list_group_spoinpo.append(element.get_text())
            
    first_group_number = int(list_group_ptk[0]) // 1000
    while first_group_number > 9:
        first_group_number %= 10
    init_list_group(first_group_number, 'ptk', list_group_ptk)
    init_list_group(first_group_number, 'pedcol', list_group_pedcol)
    init_list_group(first_group_number, 'medcol', list_group_medcol)
    init_list_group(first_group_number, 'spour', list_group_spour)
    init_list_group(first_group_number, 'spoinpo', list_group_spoinpo)

def init_get_list_group(college):
    temp = Database.execute_query(f'SELECT group_id FROM groups_students_{college}', fetch=True)
    for item in temp:
        group.append(item[0])

@bot.message_handler(commands=['start'])
def main_menu(message):
    markup_replay = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_geolacation = types.KeyboardButton('Узнать геопозицию')
    item_schedule = types.KeyboardButton('Узнать расписание')
    markup_replay.add(item_schedule, item_geolacation)
    bot.send_message(message.chat.id, 'Привет! Что вы хотите узнать?',
                     reply_markup=markup_replay)

@bot.message_handler(content_types=['text'])
def handle_all_messages(message):
    if update_lock.locked():
        bot.send_message(message.chat.id, "Сейчас происходит обновление расписания, прошу подождать пару минут (^._.^)~")
    else:
        global group, group_student, week_type, college
        
        if message.chat.id not in user_context:
            user_context[message.chat.id] = {'state': STATE_MAIN_MENU}

        user_data = user_context[message.chat.id]
        current_state = user_data.get('state', STATE_MAIN_MENU)
        
        switch = {
            STATE_MAIN_MENU: {
                'Узнать геопозицию': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_SELECTING_LOCATION, handle_geolocation),
                'Узнать расписание': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_SELECTING_SCHEDULE, handle_schedule_request),
                'Настроить ежедневные оповещения': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_SETTINGS_SELECTING_COLLEGE, handle_select_college),
                'Сброс оповещений': lambda msg: handle_reset_settings(bot, msg),
                'Главное меню': lambda msg: handle_main_menu(bot, msg),

            },
            STATE_SELECTING_LOCATION: {
                'Главный корпус': lambda msg: handle_location(bot, msg, 58.542306, 31.261174, '📍Местоположение Главного корпуса: Большая Санкт-Петербургская, 41'),
                'Политехнический колледж': lambda msg: handle_location(bot, msg, 58.541668, 31.264534, '📍Местоположение ПТК: Большая Санкт-Петербургская, 46'),
                'Антоново': lambda msg: handle_location(bot, msg, 58.541079, 31.288108, '📍Местоположение ИГУМ: район Антоново, 1'),
                'ИЦЭУС': lambda msg: handle_location(bot, msg, 58.522347, 31.258228, '📍Местоположение ИЦЭУС: Псковская улица, 3'),
                'ИМО': lambda msg: handle_location(bot, msg, 58.542809, 31.310567, '📍Местоположение ИМО: улица Державина, 6'),
                'ИБХИ': lambda msg: handle_location(bot, msg, 58.551745, 31.300628, '📍Местоположение ИБХИ: улица Советской Армии, 7'),
                'ПИ': lambda msg: handle_location(bot, msg, 58.523945, 31.262243, '📍Местоположение ПИ: улица Черняховского, 64/6'),
                'Главное меню': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_MAIN_MENU, handle_main_menu),
            },
            STATE_SELECTING_SCHEDULE: {
                'ПТК': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SELECTING_COURSE, handle_college_selection, 'ptk'),
                'СПО ИНПО': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SELECTING_COURSE, handle_college_selection, 'spoinpo'),
                'Мед.колледж': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SELECTING_COURSE, handle_college_selection, 'medcol'),
                'СПО ИЦЭУС': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SELECTING_COURSE, handle_college_selection, 'pedcol'),
                'СПО ИЮР': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SELECTING_COURSE, handle_college_selection, 'spour'),
                'Главное меню': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_MAIN_MENU, handle_main_menu),
            },
            STATE_SELECTING_COURSE: {
                '1 курс': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SELECTING_GROUP),
                '2 курс': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SELECTING_GROUP),
                '3 курс': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SELECTING_GROUP),
                '4 курс': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SELECTING_GROUP),
                '5 курс': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SELECTING_GROUP),
                '6 курс': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SELECTING_GROUP),
                'Назад': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_SELECTING_SCHEDULE, handle_schedule_request),
                'Главное меню': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_MAIN_MENU, handle_main_menu),
            },
            STATE_SELECTING_GROUP: {
                **{grp: lambda msg, group=grp: handle_transition_with_context(bot, user_context, msg, STATE_SELECTING_WEEK_TYPE, handle_group_selection, group) for grp in group},
                'Назад': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SELECTING_COURSE, handle_college_selection, user_data.get('college')),
                'Главное меню': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_MAIN_MENU, handle_main_menu),
            },
            STATE_SELECTING_WEEK_TYPE: {
                'Верхняя': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SELECTING_DAY, handle_week_selection, 'Верхняя'),
                'Нижняя': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SELECTING_DAY, handle_week_selection, 'Нижняя'),
                'Назад': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SELECTING_GROUP),  
                'Главное меню': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_MAIN_MENU, handle_main_menu),
            },
            STATE_SELECTING_DAY: {
                **{day: lambda msg, d=day: handle_display_schedule(bot, msg, user_data.get('group'), user_data.get('week_type'), d, get_schedule_ptk) for day in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']}, 
                'Назад': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SELECTING_WEEK_TYPE, handle_group_selection, user_data.get('group')),
                'Главное меню': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_MAIN_MENU, handle_main_menu),
            },
            STATE_SETTINGS_SELECTING_COLLEGE: {
                'ПТК': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SETTINGS_SELECTING_COURSE, handle_select_course, 'ptk'),
                'СПО ИНПО': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SETTINGS_SELECTING_COURSE, handle_select_course, 'spoinpo'),
                'Мед.колледж': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SETTINGS_SELECTING_COURSE, handle_select_course, 'medcol'),
                'СПО ИЦЭУС': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SETTINGS_SELECTING_COURSE, handle_select_course, 'pedcol'),
                'СПО ИЮР': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SETTINGS_SELECTING_COURSE, handle_select_course, 'spour'),
                'Назад': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_MAIN_MENU, handle_main_menu),
                'Главное меню': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_MAIN_MENU, handle_main_menu),
            },
            STATE_SETTINGS_SELECTING_COURSE: {
                '1 курс': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SETTINGS_SELECTING_GROUP),
                '2 курс': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SETTINGS_SELECTING_GROUP),
                '3 курс': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SETTINGS_SELECTING_GROUP),
                '4 курс': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SETTINGS_SELECTING_GROUP),
                '5 курс': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SETTINGS_SELECTING_GROUP),
                '6 курс': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SETTINGS_SELECTING_GROUP),
                'Назад': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_SETTINGS_SELECTING_COLLEGE, handle_select_college),
                'Главное меню': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_MAIN_MENU, handle_main_menu),
            },
            STATE_SETTINGS_SELECTING_GROUP: {
                **{grp: lambda msg, group=grp: handle_transition_with_context(bot, user_context, msg, STATE_SETTINGS_SELECTING_TIME, save_group_settings, group) for grp in group},
                'Назад': lambda msg: handle_transition_with_context(bot, user_context, msg, STATE_SETTINGS_SELECTING_COURSE, handle_select_course, user_data.get('college')),
                'Главное меню': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_MAIN_MENU, handle_main_menu),
            },
            STATE_SETTINGS_SELECTING_TIME: {
                '15:00': lambda msg: save_notification_time(bot, user_context, msg, '15:00', STATE_MAIN_MENU),
                '16:00': lambda msg: save_notification_time(bot, user_context, msg, '16:00', STATE_MAIN_MENU),
                '17:00': lambda msg: save_notification_time(bot, user_context, msg, '17:00', STATE_MAIN_MENU),
                '18:00': lambda msg: save_notification_time(bot, user_context, msg, '18:00', STATE_MAIN_MENU),
                '19:00': lambda msg: save_notification_time(bot, user_context, msg, '19:00', STATE_MAIN_MENU),
                '20:00': lambda msg: save_notification_time(bot, user_context, msg, '20:00', STATE_MAIN_MENU),
                '21:00': lambda msg: save_notification_time(bot, user_context, msg, '21:00', STATE_MAIN_MENU),
                '22:00': lambda msg: save_notification_time(bot, user_context, msg, '22:00', STATE_MAIN_MENU),
                '23:00': lambda msg: save_notification_time(bot, user_context, msg, '23:00', STATE_MAIN_MENU),
                'Назад': lambda msg: handle_show_groups(bot, user_context, user_data, msg, STATE_SETTINGS_SELECTING_GROUP),
                'Главное меню': lambda msg: handle_transition_no_context(bot, user_context, msg, STATE_MAIN_MENU, handle_main_menu),
            },
        }
        handler = switch.get(current_state, {}).get(message.text, lambda msg: handle_unknown(bot, user_context, msg, STATE_MAIN_MENU))
        handler(message)

def bot_send_location_and_message(bot, message, latitude, longitude, str):
    bot.send_location(message.chat.id, latitude, longitude)
    bot.send_message(message.chat.id, str)

def fetch_group_ids(college, group_list):
    temp = Database.execute_query(f'SELECT group_id FROM groups_students_{college}', fetch=True)
    
    for item in temp:
        group_list.append(item[0])

def init_schedule(soup):
    for number_group in group:
        link = soup.find('a', string=number_group)  
        if (link):
            link_href = link['href']
            file_url = f"https://portal.novsu.ru/{link_href}"
            response = requests.get(file_url)
            print(number_group)
            
            Database.rebuild_group_table(number_group)
            
            for day in days:
                schedule = init_schedule_ptk(number_group, day, response.content)
                if schedule != []:
                    init_send_schedule(schedule, number_group, day, "Верхняя")
                    init_send_schedule(schedule, number_group, day, "Нижняя")

def update_checked_field_notifications(user_id, college, user_group, checked, notification_time):
    query = '''
        INSERT INTO users_notifications (user_id, college, user_group, checked, time_notification)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id)
            DO UPDATE SET 
            college = EXCLUDED.college,
            user_group = EXCLUDED.user_group,
            checked = EXCLUDED.checked,
            time_notification = EXCLUDED.time_notification;
    '''
    Database.execute_query(query, (user_id, college, user_group, checked, notification_time))

def send_notifications():
    
    while True:
        while datetime.now().strftime('%M') > '00':
            time.sleep(50)
        now = datetime.now()
        current_hour = now.strftime('%H')
        
        if current_hour == '00':
            if now.weekday() == 5:
                delta = timedelta(hours=24)
            else:
                delta = timedelta(hours=14)
            next_check_time = (now + delta).replace(minute=0, second=0, microsecond=0)
            users_notifications = Database.execute_query(
                'SELECT user_id, college, user_group, time_notification FROM users_notifications WHERE checked = true',
                fetch=True
            )
            for user_id, college, user_group, notification_time in users_notifications:
                # print(f'User {user_id} has unchecked')
                update_checked_field_notifications(user_id, college, user_group, False, notification_time)
            
        else:
            next_check_time = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            
            users_notifications = Database.execute_query(
                'SELECT user_id, college, user_group, time_notification FROM users_notifications WHERE time_notification = %s AND checked = false',
                (current_hour,),
                fetch=True
            )

            
            for user_id, college, user_group, notification_time in users_notifications:
                # print(f'User {user_id} has notification time set to {notification_time}')
                
                group = user_group
                week_type = 'Верхняя' if datetime.now().isocalendar()[1] % 2 == 1 else 'Нижняя'
                
                tomorrow = now - timedelta(days=1)
                day_of_week = days[tomorrow.weekday()]
                if college == 'ptk':
                    schedule = get_schedule_ptk(group, day_of_week, week_type)
                if schedule:
                    bot.send_message(user_id, f'Напоминание на завтра: {schedule}')
                
                update_checked_field_notifications(user_id, college, user_group, True, notification_time)
            
        time.sleep((next_check_time - datetime.now()).total_seconds() - 100)

def update_database():
    print("Обновление базы данных начато")
    
    url = 'https://portal.novsu.ru/univer/timetable/spo/'
    
    response = requests.get(url)
    html = response.text

    soup = BS(html, 'html.parser')
    
    Database.rebuild_db()

    init_list_groups(soup)

    init_get_list_group('ptk')
    init_get_list_group('pedcol')
    init_get_list_group('medcol')
    init_get_list_group('spour')
    init_get_list_group('spoinpo')
                    
    fetch_group_ids('ptk', group)
    fetch_group_ids('pedcol', group)
    fetch_group_ids('medcol', group)
    fetch_group_ids('spour', group)
    fetch_group_ids('spoinpo', group)
    
    init_schedule(soup)
    
    print("Обновление базы данных завершено") 
                    
def update_thread():    
    while True:
        current_hour = datetime.now().hour
        if current_hour == 4:
            try:
                with update_lock:
                    update_database()
                
            except Exception as e:
                print(f"Error during database update: {e}")
        print(current_hour)
        time.sleep(3500)

def main():
    update_database()
    
    db_update_thread = threading.Thread(target=update_thread)
    db_update_thread.daemon = True 
    db_update_thread.start()
    
    notification_thread = threading.Thread(target=send_notifications)
    notification_thread.daemon = True
    notification_thread.start()
    
    bot.polling()

if __name__ == '__main__':
    main()