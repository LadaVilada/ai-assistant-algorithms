
def lambda_handler(event, context):
    """
    Universal Lambda handler that can route to different bot types
    """
    bot_type = event.get('bot_type', 'telegram')

    if bot_type == 'telegram':
        from ai_assistant.telegram.bot import TelegramBot
        bot = TelegramBot()
    elif bot_type == 'algorithms':
        from ai_assistant.algorithms.bot import AlgorithmBot
        bot = AlgorithmBot()
    else:
        raise ValueError(f"Unsupported bot type: {bot_type}")

    return bot.handle_lambda_event(event, context)