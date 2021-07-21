import telebot
import datetime as dt
import requests
import threading
from bs4 import BeautifulSoup


# add 3 hours to date
def f(x):
    return dt.datetime.strftime(dt.datetime.fromtimestamp(x) + dt.timedelta(hours=3), format="%H:%M")


def get_username(steamid):
    url = "https://steamcommunity.com/profiles/" + str(steamid)
    getresponse = requests.get(url)
    if getresponse.status_code != 200:
        return None
    soup = BeautifulSoup(getresponse.content, 'html.parser')
    a = soup.find("span", class_="actual_persona_name")
    if a is None:
        return None
    username = a.text
    return username


def get_appname(gameid):
    if gameid == 480:
        return "Spacewar"  # wut
    url = "https://store.steampowered.com/app/" + str(gameid)
    getresponse = requests.get(url)
    if getresponse.status_code != 200:
        return None
    soup = BeautifulSoup(getresponse.content, 'html.parser')
    a = soup.find("div", class_="apphub_AppName")
    if a is None:
        return None
    game_name = a.text
    return game_name


class TelegramNotifier:
    def __init__(self, token, chat_ids):
        self.token = token
        self.chat_ids = chat_ids
        self.bot = telebot.AsyncTeleBot(token)
        self.db_manager = None
        self.define_bot_actions()
        polling_thread = threading.Thread(target=self.bot_polling)
        polling_thread.start()

    def set_current_db(self, current_db):
        self.db_manager = current_db

    def define_bot_actions(self):
        @self.bot.message_handler(commands=['start'])
        def command_start(message):
            self.bot.reply_to(message, "Hi! This bot will help you to get playtime info about required steam profiles.")

        @self.bot.message_handler(commands=['ignore'])
        def command_ignore(message):
            if len(message.text.split()) == 2:
                try:
                    data = {"chat_id": message.chat.id, "steam_id": int(message.text.split(" ")[1])}
                    self.bot.reply_to(message, "Ok! Now ignoring that player.")
                    self.db_manager.add_ignore_entry(data)
                except ValueError:
                    self.bot.reply_to(message, "Incorrect format. Try /ignore <steam_id>")
            else:
                self.bot.reply_to(message, "Incorrect usage. Try /ignore <steam_id>")

        @self.bot.message_handler(commands=['unignore'])
        def command_unignore(message):
            if len(message.text.split()) == 2:
                try:
                    data = {"chat_id": message.chat.id, "steam_id": int(message.text.split(" ")[1])}
                    self.bot.reply_to(message, "Ok! Now stopped ignoring that player.")
                    self.db_manager.remove_ignore_entry(data)
                except ValueError:
                    self.bot.reply_to(message, "Incorrect format. Try /unignore <steam_id>")
            else:
                self.bot.reply_to(message, "Incorrect usage. Try /unignore <steam_id>")

    def bot_polling(self):
        print("Started telegram bot instance")
        self.bot.polling()

    def notify(self, data):
        s = f"" \
            f"{get_username(data['tracked_user'])} was playing " \
            f"{get_appname(data['game_id'])} " \
            f"({f(data['started_playing_timestamp'])} — {f(data['ended_playing_timestamp'])})"
        self.send_text(s, data['tracked_user'])

    def send_text(self, text, user_id):
        arr = []
        for el in self.db_manager.get_ignore_chat_ids_by_steam_id({"steam_id": user_id}):
            arr.append(el[0])
        for chat_id in self.chat_ids:
            if chat_id not in arr:
                self.bot.send_message(chat_id, text, parse_mode='Markdown')
