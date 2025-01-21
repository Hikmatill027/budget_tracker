from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, ContextTypes, filters, MessageHandler, ConversationHandler,
                          CallbackQueryHandler)
from datetime import datetime
from database import (get_summary, add_transaction, list_transactions, init_db, search_transactions, get_total_balance,
                      get_transaction_count, list_monthly_summary)

# State conversations
AMOUNT, DESCRIPTION = range(2)
DATE_DESC = range(1)

# Initialize DB
init_db()

# BOT Token
BOT_API = '7636681178:AAGSPeQ97gfAIEuTkpqqBhV3QRR_KCAZMOU'


# Starting commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰Welcome to Finance Tracker Bot💰. 💰Let's manage your budget.💰")


# async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text(f"You said: {update.message.text}")


async def add_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'step' not in context.user_data:
        await update.message.reply_text("Enter an amount.")
        context.user_data['step'] = 'amount'
        return AMOUNT
    elif context.user_data['step'] == "amount":
        try:
            amount = float(update.message.text)
            context.user_data['amount'] = amount
            await update.message.reply_text("Enter a description.")
            context.user_data['step'] = 'description'
            return DESCRIPTION
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid amount")
    elif context.user_data['step'] == 'description':
        try:
            amount = context.user_data['amount']
            description = update.message.text.lower()
            user_id = update.effective_user.id
            add_transaction(user_id, "income", amount, description)
            await update.message.reply_text(f"✅ Added income: {amount:,.0f} \n 📝Description: {description}")
            context.user_data.clear()
        except(IndexError, ValueError):
            await update.message.reply_text("❌ Please enter a valid amount")
        return ConversationHandler.END


async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'step' not in context.user_data:
        await update.message.reply_text("Enter an amount.")
        context.user_data['step'] = 'amount'
        return AMOUNT
    elif context.user_data['step'] == "amount":
        try:
            amount = float(update.message.text)
            context.user_data['amount'] = amount
            await update.message.reply_text("Enter a description.")
            context.user_data['step'] = 'description'
            return DESCRIPTION
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid amount")
    elif context.user_data['step'] == 'description':
        try:
            amount = context.user_data['amount']
            description = update.message.text.lower()
            user_id = update.effective_user.id
            add_transaction(user_id, "expense", amount, description)
            await update.message.reply_text(f"✅ Added expense: {amount:,.0f} \n 📝Description: {description}")
            context.user_data.clear()
        except (IndexError, ValueError):
            await update.message.reply_text("❌ Please enter a valid amount")
        return ConversationHandler.END


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Action canceled.")
    return ConversationHandler.END


async def show_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    total_income, total_expense = get_summary(user_id)
    total_balance = total_income - total_expense

    # The summary message
    summary_message = (
        f"💰 **Income/Expense Summary** 💰 \n"
        f"---------------------------------\n"
        f"🟢 Total Income: {total_income:,.0f} UZS\n"
        f"🔴 Total Expenses: {total_expense:,.0f} UZS\n"
        f"🟡 Balance: {total_balance:,.0f} UZS\n"
        f"---------------------------------\n"
        f"Use `/income` or `/expense` to add more entries!"
    )
    await update.message.reply_text(summary_message, parse_mode="Markdown")


async def transactions_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    page = int(context.user_data.get('page', 0))
    items_per_page = 5

    # Fetching transactions
    transaction_data = list_transactions(user_id, page, items_per_page)
    all_transactions = get_transaction_count(user_id)
    total_pages = (all_transactions + items_per_page - 1) // items_per_page

    if not transaction_data:
        await update.message.reply_text("No transaction found.")
        return

    response = "Here are your recent transactions:\n\n"
    for idx, (t_type, amount, desc, timestamp) in enumerate(transaction_data, start=page*items_per_page+1):
        response += (f"🔷 {idx}. {t_type.capitalize()} - {amount:,.0f} UZS\n "
                     f"📝 {desc.capitalize() or 'No description'}\n 📅 {timestamp}\n\n")

    # Buttons List
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page - 1}"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))

    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None
    if update.message:
        await update.message.reply_text(response, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(response)


async def pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_data = update.callback_query
    query = query_data.data

    if query.startswith("page_"):
        page = int(query.split("_")[1])
        context.user_data['page'] = page
        await transactions_list(update, context)
        await query_data.answer()


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("search funcition started")
    if 'step' not in context.user_data:
        await update.message.reply_text("Enter a description or a date in YYYY-MM-DD format")
        context.user_data['step'] = 'awaiting query'
        return
    query = update.message.text.strip()
    print("I got query")
    if not query:
        await update.message.reply_text("❌ Invalid input. Please provide with proper description or date.")
        return

    try:
        query_date = datetime.strptime(query, '%Y-%m-%d').date()
        search_key = query_date.strftime('%Y-%m-%d')
        is_data_query = True
    except ValueError:
        search_key = query.lower()
        is_data_query = False
    print("converting date")

    if not search_key:
        await update.message.reply_text("❌Invalid input. Please enter a proper date")
        return

    user_id = update.effective_user.id
    print(f"user id is {user_id}")
    try:
        search_data = search_transactions(user_id, search_key, is_data_query)
        print("No search data")
    except Exception as e:
        await update.message.reply_text(f"An error occurred during getting search data {e}")
        return

    if search_data:
        response = f"Search result for {query}:\n\n"
        for idx, (t_type, amount, desc, timestamp) in enumerate(search_data, start=1):
            response += (f"{idx}.💵 {t_type.capitalize()}: {amount:,.0f}\n📝 {desc or 'No description'}\n"
                         f"📅 {timestamp}\n\n")
    else:
        response = f"No data found matching {search_key}"

    await update.message.reply_text(response)
    context.user_data.clear()


async def monthly_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    year = int(context.args[0]) if context.args else datetime.now().year
    month = int(context.args[1]) if len(context.args) > 1 else datetime.now().month
    monthly_data = list_monthly_summary(user_id, year, month)

    total_balance = get_total_balance(user_id)
    total_income = total_balance[0] or 0
    total_expense = total_balance[1] or 0
    response = (
        f"📊 Monthly Summary for {year}-{month:02}:\n\n"
        f"💵 Total Income: {total_income:,.0f} UZS\n"
        f"💸 Total Expenses: {total_expense:,.0f} UZS\n"
        f"💰 Net Savings: {(total_income - total_expense):,.0f} UZS\n\n"
    )

    if monthly_data:
        response += "Transactions:\n\n"
        for idx, (t_type, amount, desc, timestamp) in enumerate(monthly_data, start=1):
            response += (f"🔷 {idx}. {t_type.capitalize()} - {amount:,.0f} UZS\n"
                               f"📝 {desc.capitalize() or 'No description'}\n 📅 {timestamp}\n\n")
    else:
        response += "No transaction found for this month."
    await update.message.reply_text(response)


def main():
    app = Application.builder().token(BOT_API).build()
    # Conversation Handlers
    income_handler = ConversationHandler(
        entry_points=[CommandHandler("income", add_income)],
        states={
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_income)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_income)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, fallback)],
    )
    expense_handler = ConversationHandler(
        entry_points=[CommandHandler("expense", add_expense)],
        states={
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, fallback)]
    )

    app.add_handler(CommandHandler('start', start))
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.add_handler(income_handler)
    app.add_handler(expense_handler)
    app.add_handler(CommandHandler("summary", show_summary))
    app.add_handler(CommandHandler("transactions", transactions_list))
    app.add_handler(CallbackQueryHandler(pagination, pattern="^page_"))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("report", monthly_summary))
    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
