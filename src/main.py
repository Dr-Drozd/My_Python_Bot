import random
import requests
import sqlalchemy
import telebot
import asyncio

from jokeapi import Jokes
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from telebot import types

from configDir.config import settings

#from googletrans import Translator

bot = telebot.TeleBot(settings.get_bot_token, parse_mode=None)

engine = sqlalchemy.create_engine(url=settings.get_database_url, echo=False, pool_pre_ping=True, pool_recycle=3600)

Base = declarative_base()


class Clients(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    user_id = Column(Integer)
    current_command = Column(String)
    current_data = Column(String)
    default_city = Column(String)
    default_category = Column(String)


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)


def set_city(message, user):
    new_city = message.text.strip().lower().split(' ')
    if new_city[2] != 'def':
        user.default_city = new_city[2]


def set_category(message, user):
    new_category = message.text.strip().lower().split(' ')
    if new_category[3] != 'def':
        user.default_category = new_category[3]


def create_buttons():
    markup = types.ReplyKeyboardMarkup()
    button_help = types.KeyboardButton('Помощь')
    markup.row(button_help)
    button_settings = types.KeyboardButton('Настройки')
    button_weather = types.KeyboardButton('Погода')
    markup.row(button_settings, button_weather)
    button_news = types.KeyboardButton('Новости')
    button_joke = types.KeyboardButton('Шутка')
    markup.row(button_news, button_joke)
    return markup


def on_click(message):
    if message.text.lower() == 'помощь':
        send_help(message)
    elif message.text.lower() == 'настройки':
        send_settings(message)
    elif message.text.lower() == 'погода':
        send_weather(message)
    elif message.text.lower() == 'новости':
        send_news(message)
    elif message.text.lower() == 'шутка':
        send_joke(message)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    session = Session()
    user = session.query(Clients).filter_by(user_id=message.chat.id).first()

    if not user:
        user = Clients(first_name=message.from_user.first_name,
                       last_name=message.from_user.last_name,
                       user_id=message.from_user.id,
                       current_command=message.text.strip().lower().split(' ')[0],
                       current_data="",
                       default_city="Moscow",
                       default_category="sports")
        session.add(user)
        session.commit()

    bot.send_message(message.chat.id,
                     "Добро пожаловать на дно! Я бот, и меня зовут Том, и я постараюсь помочь вам тем, чем смогу, "
                     "а пока можете выбрать интересующий вас пункт из меню.\n",
                     reply_markup=create_buttons())


@bot.message_handler(commands=['help'])
def send_help(message):
    session = Session()
    user = session.query(Clients).filter_by(user_id=message.chat.id).first()
    user.current_command = message.text.strip().lower().split(' ')[0]
    session.commit()
    bot.reply_to(message, "Сейчас я расскажу, какие есть команды и как ими пользоваться:\n\n/help - выводит "
                          "инструкцию по использованию команд\n\n/settings - выводит текущие настройки\n\n/weather "
                          "CITY - выводит данные о погоде в некотором городе CITY, который пользователь вводит сам на "
                          "английском языке\n\n/news CATEGORY - выводит некоторую новость из категории CATEGORY, "
                          "которую пользователь вводит на английском языке. Всего категорий доступно 4 штуки:\nsports "
                          "- спорт\ntechnology - технологии\nhealth - здоровье\nscience - наука\n\n/joke - выводит "
                          "случайную шутку на английском языке.")


@bot.message_handler(commands=['settings'])
def send_settings(message):
    session = Session()
    user = session.query(Clients).filter_by(user_id=message.chat.id).first()

    new_settings = message.text.strip().lower().split(' ')
    try:
        user.current_command = message.text.strip().lower().split(' ')[0]
        session.commit()
        if new_settings[1] == 'edit':
            set_city(message, user)
            set_category(message, user)
            user.current_command = message.text.strip().lower().split(' ')[0]
            user.current_data = message.text.strip().lower().split(' ')[1]
            session.commit()
            bot.send_message(message.chat.id, "Настройки успешно изменены")
        else:
            bot.send_message(message.chat.id, "Вы неверно ввели команду, изменения отменяются")
    except IndexError:
        bot.reply_to(message,
                     f"Настройки:\n\nГород: {user.default_city.capitalize()}\n\nКатегория новостей: {user.default_category}\n\nЕсли "
                     f"желаете изменить настройки, введите /settings edit arg1 arg2\n\narg1 - это город\narg2 - это "
                     f"категория новостей\n\nЕсли вы не хотите что-либо менять, заместо аргументов напишите "
                     f"def\n\nПример: /settings edit def health\n- После этого, погода будет отображаться, "
                     f"как и раньше в "
                     f"том же городе, а категория новостей будет про здоровье.")
    except KeyError:
        bot.send_message(message.chat.id, "Команда была введена некорректно")


@bot.message_handler(commands=['weather'])
def send_weather(message, weather_token=settings.get_weather_token):
    city = message.text.strip().lower().split(' ')

    session = Session()
    user = session.query(Clients).filter_by(user_id=message.chat.id).first()

    try:
        city = city[1]
        user.current_command = message.text.strip().lower().split(' ')[0]
        user.current_data = city
        session.commit()
        response = requests.get(f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_token}&units'
                                f'=metric')

        weather_data = response.json()

        general_weather = weather_data['weather'][0]['main']
        current_temp = weather_data['main']['temp']
        feels_temp = weather_data['main']['feels_like']
        pressure_value = weather_data['main']['pressure']
        humidity_value = weather_data['main']['humidity']
        wind_speed = weather_data['wind']['speed']
        bot.reply_to(message,
                     f"Погода в городе {city.capitalize()}: {general_weather}\n\nТекущая температура: {current_temp}"
                     f"°\nОщущается как: {feels_temp}°\n\nВлажность: {humidity_value}%\n\nДавление атомсферы: "
                     f"{pressure_value} ГПа\n\nСкорость ветра: {wind_speed} м/с")
    except IndexError:
        user.current_command = message.text.strip().lower().split(' ')[0]
        session.commit()
        response = requests.get(
            f'https://api.openweathermap.org/data/2.5/weather?q={user.default_city}&appid={weather_token}&units'
            f'=metric')

        weather_data = response.json()

        general_weather = weather_data['weather'][0]['main']
        current_temp = weather_data['main']['temp']
        feels_temp = weather_data['main']['feels_like']
        pressure_value = weather_data['main']['pressure']
        humidity_value = weather_data['main']['humidity']
        wind_speed = weather_data['wind']['speed']
        bot.reply_to(message,
                     f"Погода в городе {user.default_city.capitalize()}: {general_weather}\n\nТекущая температура: "
                     f"{current_temp}°\nОщущается как: {feels_temp}°\n\nВлажность: {humidity_value}%\n\nДавление "
                     f"атомсферы: {pressure_value} ГПа\n\nСкорость ветра: {wind_speed} м/с")
    except KeyError:
        bot.send_message(message.chat.id, f"Города {city} не существует или вы написали его название некорректно")


@bot.message_handler(commands=['news'])
def send_news(message, news_token=settings.get_news_token):
    session = Session()
    user = session.query(Clients).filter_by(user_id=message.chat.id).first()

    current_category = message.text.strip().lower().split(' ')
    try:
        current_category = current_category[1]
        user.current_command = message.text.strip().lower().split(' ')[0]
        user.current_data = current_category
        session.commit()
        response = requests.get(
            f'https://newsapi.org/v2/top-headlines?country=ru&category={current_category}&apiKey={news_token}')

        news_data = response.json()

        if news_data['totalResults'] > 0:
            number = random.randint(0, len(news_data['articles']) - 1)
            news_title = news_data['articles'][number]['title']
            news_author = news_data['articles'][number]['author']
            news_url = news_data['articles'][number]['url']
            bot.reply_to(message,
                         f"Самые свежие новости:\nКатегория: {current_category.capitalize()}\n\nЗаголовок: {news_title}\n\nАвтор: {news_author}\n\nСсылка: {news_url}")
        else:
            bot.reply_to(message, f"Для категории {current_category} новости не были найдены.")
    except IndexError:
        user.current_command = message.text.strip().lower().split(' ')[0]
        session.commit()

        current_category = user.default_category
        response = requests.get(
            f'https://newsapi.org/v2/top-headlines?country=ru&category={current_category}&apiKey={news_token}')

        news_data = response.json()

        if news_data['totalResults'] > 0:
            number = random.randint(0, len(news_data['articles']) - 1)
            news_title = news_data['articles'][number]['title']
            news_author = news_data['articles'][number]['author']
            news_url = news_data['articles'][number]['url']
            bot.reply_to(message,
                         f"Самые свежие новости:\n Категория: {current_category.capitalize()}\n\nЗаголовок: {news_title}\n\nАвтор: {news_author}\n\nСсылка: {news_url}")
    except KeyError:
        bot.send_message(message.chat.id, "Такой категории нет, или вы написали её некорректно, обратитесь в /help, "
                                          "если забыли имеющиеся категории")


@bot.message_handler(commands=['joke'])
def send_joke(message):
    session = Session()
    user = session.query(Clients).filter_by(user_id=message.chat.id).first()
    user.current_command = message.text.strip().lower().split(' ')[0]
    user.current_data = ""
    session.commit()

    async def print_joke():
        #translator = Translator()
        joker = await Jokes()  # Объявляем объект класса "Шутки"
        joke = await joker.get_joke(category=['programming'],
                                    blacklist=['nsfw', 'racist', 'religious', 'political', 'sexist'],
                                    lang='en',
                                    amount=1,
                                    response_format="json",
                                    )  # Получаем случайную шутку с предварительными настройками
        if joke["type"] == "single":  # Проверяем, какой формат у шутки, одна или в форме небольшого диалога
            #print(joke["joke"])
            #translation = translator.translate(joke["joke"], src='en', dest='ru')
            #print(translation)
            bot.reply_to(message, joke["joke"])
        else:
            #translation = translator.translate(joke["setup"] + "\n" + joke["delivery"], src='en', dest='ru')
            print(joke["setup"] + "\n" + joke["delivery"])
            #print(translation)
            bot.reply_to(message, joke["setup"] + "\n" + joke["delivery"])

    try:
        asyncio.run(print_joke())
    except RuntimeError:
        bot.send_message(message.chat.id, "В данный момент сервер перегружен и не может ответить на запрос")
    except KeyError:
        bot.send_message(message.chat.id, "Некорректно введена команда")


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    on_click(message)


bot.infinity_polling()
