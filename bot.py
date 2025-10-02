import os
import csv
from datetime import datetime
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)
import gspread
from google.oauth2.service_account import Credentials

# Загружаем токен из .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Инициализация Google Sheets
def init_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("lead-collector-bot-7abaa4a3f3ba.json")
    client = gspread.authorize(creds)
    sheet = client.open("Заявки от бота").sheet1
    return sheet

# Состояния диалога
ASK_NAME, ASK_PHONE = range(2)

# Файл для сохранения заявок
CSV_FILE = "leads.csv"

# Убедимся, что файл существует с заголовками
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Дата", "Имя", "Телефон"])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я помогаю оставить заявку. Как вас зовут?")
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.text.strip()
    if not user_name:
        await update.message.reply_text("Пожалуйста, введите ваше имя.")
        return ASK_NAME
    context.user_data["name"] = user_name

    # Кнопка для отправки контакта
    contact_button = KeyboardButton("📱 Отправить телефон", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Пожалуйста, отправьте ваш номер телефона, нажав кнопку ниже.",
        reply_markup=reply_markup
    )
    return ASK_PHONE

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if contact:
        phone = contact.phone_number
    else:
        # Если пользователь ввёл текст вместо контакта
        phone = update.message.text.strip()
        if not phone.isdigit() or len(phone) < 10:
            await update.message.reply_text("Пожалуйста, отправьте номер через кнопку или введите корректный номер.")
            return ASK_PHONE

    name = context.user_data.get("name", "Не указано")
    
    # Сохраняем в CSV
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, phone])

    await update.message.reply_text(
        f"Спасибо! Ваша заявка принята:\n\n👤 Имя: {name}\n📞 Телефон: {phone}"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Заявка отменена.")
    return ConversationHandler.END

def main():
    if not TOKEN:
        print("Ошибка: не найден TELEGRAM_BOT_TOKEN в .env файле!")
        return

    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PHONE: [
                MessageHandler(filters.CONTACT, ask_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    print("Бот запущен! Нажмите Ctrl+C чтобы остановить.")
    app.run_polling()

if __name__ == "__main__":
    main()