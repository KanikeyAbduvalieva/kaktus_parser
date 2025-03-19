import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from bs4 import BeautifulSoup as bs
import requests

TOKEN = '7457704240:AAF3MSkw3b9dy86ugGus95u3Dm7dBI4nqdE'
bot = telebot.TeleBot(TOKEN)

BASE_URL = "https://kaktus.media/"
news_list = []

def get_news():
    try:
        response = requests.get(BASE_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except requests.RequestException:
        return []

    soup = bs(response.text, "lxml")  # Используем lxml для быстрого парсинга
    news_blocks = soup.find_all("div", class_="Dashboard-Content-Card")[:20]

    items = []
    for block in news_blocks:
        title_tag = block.find("a", class_="Dashboard-Content-Card--name")
        if title_tag:
            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            full_link = link if link.startswith("http") else BASE_URL + link
            items.append((title, full_link))
    return items

def get_news_details(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except requests.RequestException:
        return "Описание отсутствует", None

    soup = bs(response.text, "lxml")  # Используем lxml
    desc_tag = soup.find("div", class_="BbCode")
    description = desc_tag.text.strip() if desc_tag else "Описание отсутствует"
    description = (description[:1000] + "...") if len(description) > 1000 else description

    gallery_image = soup.find("div", class_="Gallery--single-image")
    image_tag = gallery_image.find("a") if gallery_image else None
    image_url = image_tag["href"] if image_tag and image_tag.has_attr("href") else None

    return description, image_url

@bot.message_handler(commands=['start'])
def handle_start(message):
    global news_list
    news_list = get_news()
    if not news_list:
        bot.send_message(message.chat.id, "Не удалось получить новости. Попробуйте позже.")
        return

    news_text = "\n".join(f"{i+1}. {title}" for i, (title, _) in enumerate(news_list))
    bot.send_message(
        message.chat.id,
        f"Список новостей:\n{news_text}\n\nВведите номер новости:",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['quit'])
def handle_quit(message):
    global news_list
    news_list = []
    bot.send_message(message.chat.id, "Вы вышли. Введите /start для нового запуска.")

@bot.message_handler(func=lambda message: message.text.isdigit())
def handle_news_selection(message):
    global news_list
    num = int(message.text)
    if num < 1 or num > len(news_list):
        bot.send_message(message.chat.id, "Некорректный номер. Выберите от 1 до 20.")
        return

    title, link = news_list[num - 1]
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Описание", callback_data=f"desc_{num}"))
    markup.add(InlineKeyboardButton("Фото", callback_data=f"photo_{num}"))
    markup.add(InlineKeyboardButton("Назад", callback_data="back"))
    bot.send_message(
        message.chat.id,
        f"{title}\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith(("desc_", "photo_")))
def handle_inline_buttons(call):
    global news_list
    try:
        num = int(call.data.split("_")[1])
    except (IndexError, ValueError):
        bot.send_message(call.message.chat.id, "Некорректные данные.")
        return

    if num < 1 or num > len(news_list):
        bot.send_message(call.message.chat.id, "Новость не найдена. Повторите запрос через /start.")
        return

    title, link = news_list[num - 1]
    description, image_url = get_news_details(link)
    
    if call.data.startswith("desc_"):
        bot.send_message(
            call.message.chat.id,
            f"{title}\n\n{description}",
            parse_mode="Markdown"
        )
    elif call.data.startswith("photo_"):
        if image_url:
            bot.send_photo(call.message.chat.id, image_url)
        else:
            bot.send_message(call.message.chat.id, "Фото отсутствует.")

@bot.callback_query_handler(func=lambda call: call.data == "back")
def handle_back(call):
    handle_start(call.message)

if __name__ == "__main__":  # Исправил ошибку в строке
    bot.polling(non_stop=True)
