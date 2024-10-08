from telebot import types

from code.db import Database

def handle_geolocation(bot, message):
    markup_replay = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_glav = types.KeyboardButton('Главный корпус')
    item_ptk = types.KeyboardButton('Политехнический колледж')
    item_anton = types.KeyboardButton('Антоново')
    item_itys = types.KeyboardButton('ИЦЭУС')
    item_ibhi = types.KeyboardButton('ИБХИ')
    item_med = types.KeyboardButton('ИМО')
    item_ped = types.KeyboardButton('ПИ')
    item_back = types.KeyboardButton('Главное меню')
    markup_replay.add(item_glav, item_ptk, item_anton, item_itys,
                      item_ibhi, item_med, item_ped, item_back)
    bot.send_message(message.chat.id, 'Выберите интересующий институт',
                     reply_markup=markup_replay)

def handle_location(bot, message, latitude, longitude, location_message):
    bot.send_location(message.chat.id, latitude, longitude)
    bot.send_message(message.chat.id, location_message)

def handle_schedule_request_no_session(bot, message):
    markup_replay = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_ochn = types.KeyboardButton('Очное')
    item_zaoch = types.KeyboardButton('Заочное')
    item_main = types.KeyboardButton('Главное меню')
    
    markup_replay.add(item_ochn, item_zaoch).add(item_main)
    bot.send_message(message.chat.id, '📚 Выберите форму обучения', reply_markup=markup_replay)

def handle_schedule_request(bot, message):
    markup_replay = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_ochn = types.KeyboardButton('Очное')
    item_zaoch = types.KeyboardButton('Заочное')
    item_session = types.KeyboardButton('Сессия')
    item_main = types.KeyboardButton('Главное меню')
    
    markup_replay.add(item_ochn, item_zaoch, item_session).add(item_main)
    bot.send_message(message.chat.id, '📚 Выберите форму обучения', reply_markup=markup_replay)

def handle_education_form_selection(bot, message):    
    markup_replay = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_IEIS = types.KeyboardButton('ИЭИС')
    item_ITZEUS = types.KeyboardButton('ИЦЭУС')
    item_PI = types.KeyboardButton('ПИ')
    item_IBHI = types.KeyboardButton('ИБХИ')
    item_IGUM = types.KeyboardButton('ИГУМ')
    item_IMO = types.KeyboardButton('ИМО')
    item_IUR = types.KeyboardButton('ИЮР')
    item_IPT = types.KeyboardButton('ИПТ')
    item_PTI = types.KeyboardButton('ПТИ')
    item_back = types.KeyboardButton('Назад')
    item_main = types.KeyboardButton('Главное меню')
    markup_replay.add(item_IEIS, item_ITZEUS, item_PI, item_IBHI, item_IGUM, item_IMO, item_IUR, item_IPT, item_PTI).add(item_back).add(item_main)
    bot.send_message(message.chat.id, '🏫Какой колледж вас интересует?', reply_markup=markup_replay)

def handle_institute_selection(bot, user_context, message, institute_code):
    form = user_context[message.chat.id].get('form', '')
    
    institute_with_form = f'{form}_{institute_code}' if form else institute_code

    user_context[message.chat.id]['institute'] = institute_code
    
    markup_replay = generate_course_menu(institute_with_form)
    bot.send_message(message.chat.id, '❓ Какой вы курс?', reply_markup=markup_replay)

def handle_course_selection(bot, user_context, message, course, show_groups):
    current_context = user_context.get(message.chat.id, {})
    user_context[message.chat.id]['course'] = course
    selected_institute = current_context.get('institute')
    if selected_institute == 'ptk':
        show_groups(message, 'groups_students_ptk')
    elif selected_institute == 'spoinpo':
        show_groups(message, 'groups_students_spoinpo')

def handle_show_groups(bot, user_context, message, next_state):
    user_context[message.chat.id]['state'] = next_state
    markup_replay = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if message.text[0].isdigit():
        user_context[message.chat.id]['course'] = message.text[0]  
    
    form = user_context[message.chat.id].get('form')
    course = user_context[message.chat.id].get('course') 
    institute = user_context[message.chat.id].get('institute') if form is None else f"{form}_{user_context[message.chat.id].get('institute')}"
    
    
    conn = Database.get_connection()
    try:
        temp = Database.execute_query("SELECT group_id FROM groups_students_{} WHERE group_course=%s".format(institute), (course,), fetch=True)
        
        temp_items = []
        for item in temp:
            temp_items.append(types.KeyboardButton(item[0]))
        
        markup_replay.add(*temp_items)
    finally:
        conn.close()
        
    markup_replay.add(types.KeyboardButton('Назад')).add(types.KeyboardButton('Главное меню'))
    bot.send_message(message.chat.id, '📝Выберите свою группу', reply_markup=markup_replay)


def handle_group_selection(bot, user_context, message, group):
    user_context[message.chat.id]['group'] = group
    markup_replay = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup_replay.add(types.KeyboardButton('Верхняя'), types.KeyboardButton('Нижняя'))
    markup_replay.add(types.KeyboardButton('Назад')).add(types.KeyboardButton('Главное меню'))
    bot.send_message(message.chat.id, '❓ Выберите тип недели', reply_markup=markup_replay)

def handle_week_selection(bot, user_context, message, week_type):
    user_context[message.chat.id]['week_type'] = week_type
    markup_replay = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup_replay.add(*[types.KeyboardButton(day) for day in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']])
    markup_replay.add(types.KeyboardButton('Назад')).add(types.KeyboardButton('Главное меню'))
    bot.send_message(message.chat.id, '📅 Выберите день недели', reply_markup=markup_replay)

def handle_display_schedule(bot, message, group, week_type, day, get_schedule_ptk):
    schedule = get_schedule_ptk(group, day, week_type)
    if schedule:
        bot.send_message(message.chat.id, f'Расписание на {day}, неделя - {week_type}, группа - {group}:\n' + '\n'.join(schedule))
    else:
        bot.send_message(message.chat.id, 'Нет занятий')

def handle_main_menu(bot, message):
    markup_replay = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_geolocation = types.KeyboardButton('Узнать геопозицию')
    item_schedule = types.KeyboardButton('Узнать расписание')
    item_settings = types.KeyboardButton('Настроить ежедневные оповещения')
    item_setting_reset = types.KeyboardButton('Сброс оповещений')
    markup_replay.add(item_schedule).add(item_geolocation).add(item_settings).add(item_setting_reset)
    bot.send_message(message.chat.id, 'Главное меню', reply_markup=markup_replay)

def handle_unknown(bot, user_state, message, STATE_MAIN_MENU):
    current_state = user_state.get(message.chat.id, {}).get('state', STATE_MAIN_MENU)
    markup_replay = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if current_state != STATE_MAIN_MENU:
        item_back = types.KeyboardButton('Назад')
        markup_replay.add(item_back)
    item_main_menu = types.KeyboardButton('Главное меню')
    markup_replay.add(item_main_menu)
    
    bot.send_message(message.chat.id, '⚠️Извините, я вас не понимаю.\nCлeдyйтe кнопкам меню!⚠️',
                     reply_markup=markup_replay)

def handle_transition_with_context(bot, user_context, message, next_state, handler, *args):
    user_context[message.chat.id]['state'] = next_state
    handler(bot, user_context, message, *args)

def handle_transition_no_context(bot, user_context, message, next_state, handler, *args):
    user_context[message.chat.id]['state'] = next_state
    handler(bot, message, *args)

# def handle_select_institute(bot, message):
#     markup_replay = types.ReplyKeyboardMarkup(resize_keyboard=True)
#     item_ptk = types.KeyboardButton('ПТК')
#     item_spoinpo = types.KeyboardButton('СПО ИНПО')
#     item_medcol = types.KeyboardButton('Мед.колледж')
#     item_pedcol = types.KeyboardButton('СПО ИЦЭУС')
#     item_spour = types.KeyboardButton('СПО ИЮР')
#     item_back = types.KeyboardButton('Назад')
#     markup_replay.add(item_ptk, item_spoinpo, item_medcol, item_pedcol, item_spour, item_back)
#     bot.send_message(message.chat.id, 'Выберите колледж', reply_markup=markup_replay)
    
def handle_select_institute_with_form(bot, user_context, message, form):
    user_context[message.chat.id]['form'] = form
    handle_education_form_selection(bot, message)

# def handle_select_course(bot, user_context, message, institute):
#     user_context[message.chat.id]['institute'] = institute
#     markup_replay = generate_course_menu(institute)
#     bot.send_message(message.chat.id, 'Выберите курс', reply_markup=markup_replay)
    
def handle_reset_settings(bot, message):
    Database.execute_query(f"DELETE FROM users_notifications WHERE user_id = {message.chat.id}")
    bot.send_message(message.chat.id, 'Ежедневные оповещения отключены')
    handle_main_menu(bot, message)
    
def save_group_settings(bot, user_context, message, group):
    user_context[message.chat.id]['group'] = group
    markup_replay = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    item_15 = types.KeyboardButton('15:00')
    item_16 = types.KeyboardButton('16:00')
    item_17 = types.KeyboardButton('17:00')
    item_18 = types.KeyboardButton('18:00')
    item_19 = types.KeyboardButton('19:00')
    item_20 = types.KeyboardButton('20:00')
    item_21 = types.KeyboardButton('21:00')
    item_22 = types.KeyboardButton('22:00')
    item_23 = types.KeyboardButton('23:00')
    item_back = types.KeyboardButton('Назад')
    item_main_menu = types.KeyboardButton('Главное меню')
    
    markup_replay.add(item_15, item_16, item_17, item_18, item_19, item_20, item_21, item_22, item_23).add(item_back).add(item_main_menu)
    bot.send_message(message.chat.id, 'Выберите время для рассылки оповещения', reply_markup=markup_replay)

def save_notification_time(bot, user_context, message, time_notification, state):
    user_id = message.chat.id
    user_data = user_context.get(user_id, {})

    form = user_data.get('form')
    
    institute = user_data.get('institute') if form is None else f"{form}_{user_data.get('institute')}"
    user_group = user_data.get('group')

    query = '''
        INSERT INTO users_notifications (user_id, institute, user_group, checked, time_notification)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id)
            DO UPDATE SET 
            institute = EXCLUDED.institute,
            user_group = EXCLUDED.user_group,
            checked = EXCLUDED.checked,
            time_notification = EXCLUDED.time_notification;
    '''
    Database.execute_query(query, (user_id, institute, user_group, False, time_notification[:2]))

    user_context[user_id]['state'] = state
    bot.send_message(user_id, f'Настройки обновлены')
    handle_main_menu(bot, message)
    
def generate_course_menu(institute):
    markup_replay = types.ReplyKeyboardMarkup(resize_keyboard=True)
    course_list = sorted(fetch_institute_courses(institute))
    
    for course in course_list:
        markup_replay.add(types.KeyboardButton(f'{course} курс'))
    
    item_main = types.KeyboardButton('Главное меню')
    item_back = types.KeyboardButton('Назад')
    markup_replay.add(item_back).add(item_main)
    return markup_replay

def fetch_institute_courses(institute):
    temp = Database.execute_query(f'SELECT DISTINCT group_course FROM groups_students_{institute}', fetch=True)
    course_list = []
    
    for item in temp:
        course_list.append(item[0])
    return course_list