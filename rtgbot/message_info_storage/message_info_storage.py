from abc import ABC

from rtgbot.etities.message_info import TgMessageInfo


class TgMessageInfoStorage(ABC):
    async def get(self, chat_id: int, message_key: str):
        raise NotImplementedError

    async def get_all(self, chat_id: int):
        raise NotImplementedError

    async def add(self, chat_id: int, message_key: str, message_info: TgMessageInfo):
        raise NotImplementedError

    async def remove(self, chat_id: int, message_id: int):
        raise NotImplementedError

    async def remove_all(self, chat_id: int):
        raise NotImplementedError
