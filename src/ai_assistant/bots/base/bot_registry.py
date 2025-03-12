class BotRegistry:
    _bots = {}

    @classmethod
    def register(cls, bot_type, bot_class):
        cls._bots[bot_type] = bot_class

    @classmethod
    def get_bot(cls, bot_type):
        return cls._bots.get(bot_type)
