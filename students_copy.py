#!/usr/local/bin/python3.10
from multiprocessing import Process, Pipe

a, b = Pipe()

def f():
    try:
        import telebot
        import gspread
        from datetime import datetime

        # Подключение к таблице
        gc = gspread.service_account()
        sh = gc.open("for bot")

        # Приветствие
        WELCOME_MESSAGE = '''Вас приветствует бот для отметки присутствия студентов на лекции. Чтобы отметить студентов, введите команду: /lesson_start.'''

        # меню
        menu = ['В начало', 'Список присутствующих', 'Сбросить выбор', 'Подтвердить выбор']

        # api-key бота
        with open('/home/bot_user/bot/auth_info.txt', 'r', encoding='utf-8') as f:
            auth_info = f.readline()[:-1]

        bot = telebot.TeleBot(auth_info)

        @bot.message_handler(commands=['start'])
        def welcome(message):
            bot.send_message(message.from_user.id, WELCOME_MESSAGE, parse_mode="HTML")

        @bot.message_handler(commands=['lesson_start'])
        def step_1(message):
            # получение данных из таблицы
            main_dict = dict()

            worksheets = sh.worksheets()
            worksheets_title = [i.title for i in worksheets]
            main_dict['groups'] = dict()

            for i in worksheets_title[1:]:
                l = sh.worksheet(i).get_all_values()
                main_dict['groups'].update({i:{'students':l[0][1:], 'records': len(l)}})

            worksheet = sh.worksheet(worksheets_title[0])
            list_of_dicts = worksheet.get_all_records()
            for k in list_of_dicts[0].keys():
                main_dict.update({k:[]})
            for i in list_of_dicts:
                for k, v in i.items():
                    if v != '':
                        main_dict[k] += [v]

            if message.from_user.username not in main_dict['teachers']:
                bot.send_message(message.from_user.id, 'К сожалению, вас нет с списке преподавателей. =(', parse_mode="HTML")
            else:
                result = {
                    'date': '',
                    'teacher': '',
                    'audience': '',
                    'group_id': '',
                    'students_list': [],
                }
                result['date'] = datetime.now().strftime("%d-%m-%Y")
                result['teacher'] = '@' + message.from_user.username
                keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                for audience in main_dict['audiences']:
                    keyboard.add(telebot.types.KeyboardButton(text = audience))
                msg = bot.send_message(
                            message.from_user.id,
                            'На дополнительной клавиатуре выбирете аудиторию.',
                            parse_mode="HTML",
                            reply_markup=keyboard)
                bot.register_next_step_handler(msg, step_2, [result, main_dict])

        def step_2(message, args):
            result, main_dict = args
            result['audience'] = message.text
            keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            for group in main_dict['groups'].keys():
                keyboard.add(telebot.types.KeyboardButton(text = group))
            msg = bot.send_message(
                            message.from_user.id,
                            'На дополнительной клавиатуре выбирете группу.',
                            parse_mode="HTML",
                            reply_markup=keyboard)
            bot.register_next_step_handler(msg, step_3, [result, main_dict])

        def step_3(message, args):
            result, main_dict = args
            if message.text in main_dict['groups']:
                result['group_id'] = message.text

            keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            for student in main_dict['groups'][result['group_id']]['students']:
                keyboard.add(telebot.types.KeyboardButton(text = student))
            keyboard.row(
                telebot.types.KeyboardButton(text = menu[0]),
                telebot.types.KeyboardButton(text = menu[1]),
                telebot.types.KeyboardButton(text = menu[2]),
                telebot.types.KeyboardButton(text = menu[3]),
            )
            msg = bot.send_message(
                            message.from_user.id,
                            'Отметьте присутствующего студента:',
                            parse_mode="HTML",
                            reply_markup=keyboard)
            bot.register_next_step_handler(msg, step_4, [result, main_dict])

        def step_4(message, args):
            result, main_dict = args
            if message.text == 'В начало':
                step_1(message)
            elif message.text == 'Список присутствующих':
                if len(result['students_list']) != 0:
                    m = '<b>Аудитория:</b>\n\t' + result['audience'] + '\n\n' + '<b>Группа:</b>\n\t' + result['group_id'] + '\n\n' + '<b>Присутствующие:</b>\n\t - '+'\n\t - '.join(result['students_list'])
                else:
                    m = 'Список пока пуст. =('
                bot.send_message(message.from_user.id, m, parse_mode="HTML")
                step_3(message, args)
            elif message.text == 'Сбросить выбор':
                result['students_list'] = []
                step_3(message, args)
            elif message.text == 'Подтвердить выбор':
                #print(result)
                bot.send_message(
                            message.from_user.id,
                            '<b>Аудитория:</b>\n\t' + result['audience'] + '\n\n' + '<b>Группа:</b>\n\t' + result['group_id'] + '\n\n' + '<b>Присутствующие:</b>\n\t - '+'\n\t - '.join(result['students_list']) + '\n\nДля повтора введите команду /lesson_start',
                            parse_mode="HTML",
                            reply_markup=telebot.types.ReplyKeyboardRemove())
                plus_list = ["'+" for i in range(len(main_dict['groups'][result['group_id']]['students']))]
                absent_students = set(main_dict['groups'][result['group_id']]['students']) - set(result['students_list'])
                absent_students = list(absent_students)
                for i in absent_students:
                    plus_list[main_dict['groups'][result['group_id']]['students'].index(i)] = "'-"
                plus_list = [result['date']] + plus_list
                for i, val in enumerate(plus_list):
                    sh.worksheet(result['group_id']).update_cell(main_dict['groups'][result['group_id']]['records']+1, i+1, val)
            else:
                result['students_list'].append(message.text)
                step_3(message, args)

        bot.polling(none_stop=True, interval=0)
    except Exception as ex:
        b.send(ex)

if __name__ == '__main__':
    while True:
        p = Process(target=f)
        p.start()
        print(a.recv())
        p.join()
