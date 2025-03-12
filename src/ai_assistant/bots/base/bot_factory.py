from src.ai_assistant.bots.base.bot_registry import BotRegistry


class BotFactory:
    @staticmethod
    def create_bot(bot_type, **dependencies):
        bot_class = BotRegistry.get_bot(bot_type)
        if not bot_class:
            raise ValueError(f"No bot registered for type: {bot_type}")
        return bot_class(**dependencies)