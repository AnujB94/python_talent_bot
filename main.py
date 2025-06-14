from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import excel_utils
import nlp_utls
import os
from flask import Flask, request
import logging

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize Flask app
app = Flask(__name__)

# Step tracking
user_states = {}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Actor", callback_data='actor')],
        [InlineKeyboardButton("Recruiter", callback_data='recruiter')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Are you an Actor or Recruiter?", reply_markup=reply_markup)

# Handle button click
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    role = query.data

    if role == 'actor':
        await query.edit_message_text("Please enter your full name:")
        user_states[query.from_user.id] = {'role': 'actor', 'step': 'name'}
    elif role == 'recruiter':
        await query.edit_message_text("Tell us what kind of actor you're looking for.")
        user_states[query.from_user.id] = {'role': 'recruiter', 'step': 'search'}

# Handle messages
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = user_states.get(user_id)

    if not state:
        return

    text = update.message.text.strip()

    if state['role'] == 'actor':
        step = state.get('step')
        if step == 'name':
            state['name'] = text
            state['step'] = 'phone'
            await update.message.reply_text("Enter your phone number:")
        elif step == 'phone':
            state['phone'] = text
            state['step'] = 'age'
            await update.message.reply_text("Enter your age:")
        elif step == 'age':
            try:
                state['age'] = int(text)
                state['step'] = 'gender'
                await update.message.reply_text("Enter your gender (Male/Female):")
            except:
                await update.message.reply_text("Invalid age. Please enter again.")
        elif step == 'gender':
            state['gender'] = text
            await update.message.reply_text("Do you want to pay so recruiters can contact you directly? (Yes/No)")
            state['step'] = 'paid'
        elif step == 'paid':
            paid = text.lower() in ['yes', 'y']
            excel_utils.add_actor_to_excel(
                state['name'],
                state['phone'],
                state['age'],
                state['gender'],
                paid
            )
            await update.message.reply_text("Thanks! You're all set.")
            del user_states[user_id]

    elif state['role'] == 'recruiter':
        parsed = nlp_utls.parse_user_query(text)
        results = excel_utils.search_actors_in_excel(**parsed)

        if not results:
            await update.message.reply_text("No matching actors found.")
            return

        for actor in results:
            msg = f"Name: {actor['name']}\nAge: {actor['age']}\nGender: {actor['gender']}"
            keyboard = [[InlineKeyboardButton("Contact", callback_data=f"contact_{actor['phone']}_{actor['paid']}")]]
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# Contact button handler
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, phone, paid = query.data.split('_')

    if paid == 'True':
        await query.message.reply_text(f"Contact: {phone}")
    else:
        await query.message.reply_text("Contact: +918999272213")

# Initialize bot
TOKEN = os.getenv("BOT_TOKEN")
application = Application.builder().token(TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
application.add_handler(CallbackQueryHandler(contact_handler, pattern=r'^contact_'))

# Initialize Excel file
excel_utils.ensure_excel_file()

# Flask routes
@app.route('/')
def index():
    return 'Bot is running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), application.bot)
    application.process_update(update)
    return 'ok'

def main():
    # Get the port from environment variable or default to 10000
    port = int(os.environ.get('PORT', 10000))
    
    # Set webhook
    webhook_url = os.environ.get('WEBHOOK_URL')
    if webhook_url:
        application.bot.set_webhook(url=f'{webhook_url}/webhook')
        print(f"Webhook set to {webhook_url}/webhook")
    
    # Start Flask server
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()