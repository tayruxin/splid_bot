# 💸 Splid_bot

A simple Telegram bot to split expenses among friends during outings. Easily record who paid, who owes, and settle up at the end!

## 🚀 Features

- Split expenses fairly among multiple people
- Keep track of payments and balances
- View all past expenses
- Calculate who owes whom
- Clear and reset groups anytime

## 🤖 Bot Commands

| Command           | Description |
|------------------|-------------|
| `/start`          | Initialize the bot for your group. You'll be prompted to enter the number of people and their names. You'll also set the currency (e.g., SGD, USD). |
| `/add`            | Add a new expense. You'll be guided to choose payers, payees, provide a description, and enter the amount. The bot automatically calculates fair splits. |
| `/view`           | View all the expenses recorded so far in your group, including who paid and who the expense was for. |
| `/settleup`       | See the final balances for everyone. The bot will show who should pay whom and how much to settle all expenses fairly. |
| `/deleteexpense`  | Choose and delete a specific expense from the recorded list. Useful for correcting mistakes. |
| `/clear_expenses` | Remove all recorded expenses while keeping the group setup intact. Useful to start fresh without re-adding everyone. |
| `/deletegroup`    | Completely reset the group, removing all members and expenses. This allows a full restart of the setup process. |

## 🧠 Flow of `/add` Command

1. Select **who paid** (multiple payers allowed)
2. Select **who the expense is for** (payees)
3. Enter **expense description**
4. Enter **expense amount**

The bot will then calculate how much each person owes or is owed, based on equal splitting.

## 🛠 Setup

### Prerequisites

- Python 3.7+
- A Telegram bot token (create one with [@BotFather](https://t.me/BotFather))

### Installation

1. Clone the repo:

   ```bash
   git clone https://github.com/tayruxin/splid_bot.git
   cd splid_bot
