import telebot
from dotenv import load_dotenv
import os
from telebot import types

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)


commands = [
    types.BotCommand("start", "Start the bot"),
    types.BotCommand("add", "Add an expense"),
    types.BotCommand("view", "View expenses"),
    types.BotCommand("settleup", "Settle expenses"),
    types.BotCommand("deleteexpense", "Delete an expense"),
    types.BotCommand("clear_expenses", "Clear all expenses"),
    types.BotCommand("deletegroup", "Delete the group"),
]

# Set the commands (do this once on bot start)
bot.set_my_commands(commands)

user_state = {}
user_data = {}

# Define states
ASKING_NUMBER = 1
ASKING_NAMES = 2
ASKING_CURRENCY = 3
ADDING_PAYER = 4
ADDING_PAYEES = 5
ADDING_DESCRIPTION = 6
ADDING_AMOUNT = 7
DELETING_EXPENSE = 8

@bot.message_handler(commands=['start'])
def send_starting_option(message):
    user_id = message.chat.id
    user_state[user_id] = {'step': ASKING_NUMBER}
    print(f"[DEBUG] User {user_id} started setup, step: ASKING_NUMBER")
    bot.reply_to(message, "How many people are there (including you)?")

@bot.message_handler(commands=['add'])
def start_add(message):
    user_id = message.chat.id
    data = user_data.get(user_id)
    if not data:
        bot.reply_to(message, "Please use /start to setup the group first.")
        print(f"[DEBUG] User {user_id} tried /add but no setup found.")
        return

    # Reset and initialize state for adding expense
    user_state[user_id] = {
        'step': ADDING_PAYER,
        'selected_payers': [],
        'selected_payees': [],
        'expense': {}
    }
    print(f"[DEBUG] User {user_id} started adding expense, step: ADDING_PAYER")

    markup = generate_selection_markup(data['friend_names'], [], 'payer')
    bot.send_message(user_id, "Who is paying? (Click names to select, then press ✅ Done)", reply_markup=markup)

def generate_selection_markup(names, selected_list, prefix):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for i, name in enumerate(names):
        label = f"✅ {name}" if name in selected_list else name
        buttons.append(types.InlineKeyboardButton(label, callback_data=f"{prefix}:{i}"))
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("✅ Done", callback_data=f"done_{prefix}s"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith(("payer:", "payee:")))
def handle_selection(call):
    user_id = call.message.chat.id
    state = user_state.get(user_id)
    if not state:
        print(f"[DEBUG] User {user_id} callback but no state found.")
        return

    if call.data.startswith("payer:"):
        prefix = 'selected_payers'
        short_prefix = 'payer'
    else:
        prefix = 'selected_payees'
        short_prefix = 'payee'

    idx = int(call.data.split(":")[1])
    name = user_data[user_id]['friend_names'][idx]

    if name in state[prefix]:
        state[prefix].remove(name)
        print(f"[DEBUG] User {user_id} removed {name} from {prefix}")
    else:
        state[prefix].append(name)
        print(f"[DEBUG] User {user_id} added {name} to {prefix}")

    markup = generate_selection_markup(user_data[user_id]['friend_names'], state[prefix], short_prefix)
    try:
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        print(f"[ERROR] Failed to edit message reply markup: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("done_"))
def handle_done_selection(call):
    user_id = call.message.chat.id
    state = user_state.get(user_id)

    if not state:
        print(f"[DEBUG] User {user_id} done callback but no state found.")
        return

    done_type = call.data.split("_")[1]
    print(f"[DEBUG] User {user_id} clicked done on {done_type}, current step: {state['step']}")

    if done_type == "payers":
        if not state['selected_payers']:
            bot.answer_callback_query(call.id, "Please select at least one payer.")
            print(f"[DEBUG] User {user_id} tried to finish payer selection with none selected.")
            return
        # Move to selecting payees
        state['step'] = ADDING_PAYEES
        print(f"[DEBUG] User {user_id} moving to step ADDING_PAYEES")
        markup = generate_selection_markup(user_data[user_id]['friend_names'], [], 'payee')
        try:
            bot.edit_message_text(
                "Who is this expense for? (Select names then press ✅ Done)",
                chat_id=user_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except Exception as e:
            print(f"[ERROR] Failed to edit message for payee selection: {e}")
            bot.send_message(user_id, "Who is this expense for? (Select names then press ✅ Done)", reply_markup=markup)

    elif done_type == "payees":
        if not state['selected_payees']:
            bot.answer_callback_query(call.id, "Please select at least one payee.")
            print(f"[DEBUG] User {user_id} tried to finish payee selection with none selected.")
            return
        # Move to entering description
        state['step'] = ADDING_DESCRIPTION
        print(f"[DEBUG] User {user_id} moving to step ADDING_DESCRIPTION")
        try:
            bot.edit_message_text(
                "Enter the name/description of the expense:",
                chat_id=user_id,
                message_id=call.message.message_id
            )
        except Exception as e:
            print(f"[ERROR] Failed to edit message for description input: {e}")
            bot.send_message(user_id, "Enter the name/description of the expense:")

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get('step') == ADDING_DESCRIPTION)
def handle_description(message):
    user_id = message.chat.id
    state = user_state[user_id]
    state['expense']['description'] = message.text.strip()
    state['step'] = ADDING_AMOUNT
    print(f"[DEBUG] User {user_id} entered description: {state['expense']['description']}, moving to ADDING_AMOUNT")
    bot.reply_to(message, "Enter the amount spent:")

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get('step') == ADDING_AMOUNT)
def handle_amount(message):
    user_id = message.chat.id
    state = user_state[user_id]
    try:
        amount = float(message.text.strip())
        expense = {
            'payers': state['selected_payers'],
            'payees': state['selected_payees'],
            'description': state['expense']['description'],
            'amount': amount
        }
        user_data[user_id]['expenses'].append(expense)
        print(f"[DEBUG] User {user_id} added expense: {expense}")
        bot.reply_to(
            message,
            f"✅ Expense added: {expense['description']} - {amount} {user_data[user_id]['currency']}"
        )
        del user_state[user_id]
    except ValueError:
        print(f"[DEBUG] User {user_id} entered invalid amount: {message.text}")
        bot.reply_to(message, "Please enter a valid amount.")

@bot.message_handler(commands=['deleteexpense'])
def delete_expense_start(message):
    user_id = message.chat.id
    data = user_data.get(user_id)
    if not data or not data.get('expenses'):
        bot.reply_to(message, "No expenses recorded yet to delete.")
        print(f"[DEBUG] User {user_id} tried to delete expense but none found.")
        return
    
    lines = []
    for i, e in enumerate(data['expenses']):
        lines.append(
            f"{i+1}. {e['description']} - {e['amount']} {data['currency']}\n"
            f"   Paid by: {', '.join(e['payers'])}\n"
            f"   For: {', '.join(e['payees'])}"
        )
    bot.reply_to(message, "Which expense number do you want to delete?\n\n" + "\n\n".join(lines))
    
    user_state[user_id] = {'step': DELETING_EXPENSE}
    print(f"[DEBUG] User {user_id} started deleting expense, waiting for input.")

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get('step') == DELETING_EXPENSE)
def handle_delete_expense(message):
    user_id = message.chat.id
    state = user_state[user_id]
    data = user_data.get(user_id)

    try:
        idx = int(message.text.strip()) - 1
        if idx < 0 or idx >= len(data['expenses']):
            raise IndexError
        deleted_expense = data['expenses'].pop(idx)
        bot.reply_to(message, f"✅ Deleted expense: {deleted_expense['description']} - {deleted_expense['amount']} {data['currency']}")
        print(f"[DEBUG] User {user_id} deleted expense at index {idx}: {deleted_expense}")
        del user_state[user_id]
    except (ValueError, IndexError):
        print(f"[DEBUG] User {user_id} entered invalid delete index: {message.text}")
        bot.reply_to(message, "Please enter a valid expense number from the list.")

@bot.message_handler(commands=['view'])
def view_expenses(message):
    user_id = message.chat.id
    data = user_data.get(user_id)
    if not data or not data.get('expenses'):
        bot.reply_to(message, "No expenses recorded yet.")
        print(f"[DEBUG] User {user_id} viewed expenses but none recorded.")
        return

    lines = []
    for i, e in enumerate(data['expenses']):
        lines.append(
            f"{i+1}. {e['description']} - {e['amount']} {data['currency']}\n"
            f"   Paid by: {', '.join(e['payers'])}\n"
            f"   For: {', '.join(e['payees'])}"
        )
    bot.reply_to(message, "\n\n".join(lines))
    print(f"[DEBUG] User {user_id} viewed expenses.")

@bot.message_handler(commands=['clear_expenses'])
def clear_expenses(message):
    user_id = message.chat.id
    data = user_data.get(user_id)
    if not data:
        bot.reply_to(message, "No group setup found. Use /start to set up.")
        print(f"[DEBUG] User {user_id} tried /clear_expenses but no setup found.")
        return

    data['expenses'].clear()
    bot.reply_to(message, "✅ All expenses cleared.")
    print(f"[DEBUG] User {user_id} cleared all expenses.")


@bot.message_handler(commands=['deletegroup'])
def delete_group(message):
    user_id = message.chat.id
    if user_id in user_data:
        del user_data[user_id]
    if user_id in user_state:
        del user_state[user_id]
    bot.reply_to(message, "🗑️ Group data deleted. Please /start to set up a new group.")
    print(f"[DEBUG] User {user_id} deleted group data.")

@bot.message_handler(commands=['settleup'])
def settleup(message):
    user_id = message.chat.id
    data = user_data.get(user_id)
    if not data or not data.get('expenses'):
        bot.reply_to(message, "No expenses to settle.")
        return

    balances = {name: 0.0 for name in data['friend_names']}
    for e in data['expenses']:
        split_amount = e['amount'] / len(e['payees'])
        for payer in e['payers']:
            balances[payer] += e['amount'] / len(e['payers'])
        for payee in e['payees']:
            balances[payee] -= split_amount

    lines = []
    for name, bal in balances.items():
        if bal > 0:
            lines.append(f"{name} should receive {bal:.2f} {data['currency']}")
        elif bal < 0:
            lines.append(f"{name} owes {-bal:.2f} {data['currency']}")
        else:
            lines.append(f"{name} is settled.")

    # Suggested payments
    creditors = sorted([(n, b) for n, b in balances.items() if b > 0], key=lambda x: -x[1])
    debtors = sorted([(n, b) for n, b in balances.items() if b < 0], key=lambda x: x[1])
    suggestions = []

    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor, d_amt = debtors[i]
        creditor, c_amt = creditors[j]
        amount = min(-d_amt, c_amt)
        suggestions.append(f"{debtor} pays {creditor} {amount:.2f} {data['currency']}")
        balances[debtor] += amount
        balances[creditor] -= amount
        if abs(balances[debtor]) < 1e-6:
            i += 1
        if abs(balances[creditor]) < 1e-6:
            j += 1

    output = "\n".join(lines)
    if suggestions:
        output += "\n\n💡 Suggested payments:\n" + "\n".join(suggestions)

    bot.reply_to(message, output)

    print(f"[DEBUG] User {user_id} settled up with balances: {balances}")

@bot.message_handler(func=lambda message: message.chat.id in user_state)
def handle_start_setup(message):
    user_id = message.chat.id
    state = user_state[user_id]

    if state['step'] == ASKING_NUMBER:
        try:
            num = int(message.text)
            if num <= 0:
                raise ValueError
            state['num_friends'] = num
            state['step'] = ASKING_NAMES
            state['friend_names'] = []
            state['current_name'] = 0
            print(f"[DEBUG] User {user_id} entered number of friends: {num}, moving to ASKING_NAMES")
            bot.reply_to(message, f"Enter name of person 1:")
        except ValueError:
            print(f"[DEBUG] User {user_id} entered invalid number of friends: {message.text}")
            bot.reply_to(message, "Please enter a valid number greater than 0.")

    elif state['step'] == ASKING_NAMES:
        state['friend_names'].append(message.text.strip())
        state['current_name'] += 1
        print(f"[DEBUG] User {user_id} entered friend name: {message.text.strip()} ({state['current_name']}/{state['num_friends']})")
        if state['current_name'] < state['num_friends']:
            bot.reply_to(message, f"Enter name of person {state['current_name'] + 1}:")
        else:
            state['step'] = ASKING_CURRENCY
            print(f"[DEBUG] User {user_id} finished entering names, moving to ASKING_CURRENCY")
            bot.reply_to(message, "Enter the currency code (e.g. SGD):")

    elif state['step'] == ASKING_CURRENCY:
        currency = message.text.strip().upper()
        # Save data globally
        user_data[user_id] = {
            'friend_names': state['friend_names'],
            'currency': currency,
            'expenses': []
        }
        print(f"[DEBUG] User {user_id} setup completed with currency: {currency}")
        bot.reply_to(message, 
                      f"✅ Setup complete!\n"
                       f"👥 People: {state['friend_names']}\n"
                        f"💰 Currency: {currency}\n"
                         f"Use /add to record a new expense."
                      )
        del user_state[user_id]

bot.infinity_polling()
