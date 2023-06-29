import typing as tp

from collections import defaultdict

from rtgbot.etities.message_info import TgMessageInfo
from rtgbot.message_info_storage.message_info_storage import TgMessageInfoStorage


class MemoryTgMessageInfoStorage(TgMessageInfoStorage):
    def __init__(self):
        self.user_messages: tp.Dict[int, tp.List[(str, TgMessageInfo)]] = defaultdict(list)

    async def get(self, chat_id: int, message_key: str):
        return list(filter(lambda item: item[0] == message_key, self.user_messages[chat_id]))[0][1]

    async def get_all(self, chat_id: int):
        return list(map(lambda item: item[1], self.user_messages[chat_id]))

    async def add(self, chat_id: int, message_key: str, message_info: TgMessageInfo):
        self.user_messages[chat_id].append((message_key, message_info))

    async def remove(self, chat_id: int, message_id: int):
        self.user_messages[chat_id] = list(filter(lambda item: item[1].message_id != message_id, self.user_messages[chat_id]))

    async def remove_all(self, chat_id: int):
        self.user_messages[chat_id].clear()
