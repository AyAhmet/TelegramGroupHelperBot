import telegram_group_helper_bot


def entry(request):
    bot = telegram_group_helper_bot.TelegramGroupHelper()
    bot.update_handler(request.get_json(force=True))
    return "OKAY"

