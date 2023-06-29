import asyncio
import copy
import logging

import typing as tp

import aiogram
from aiogram import Bot, Dispatcher, Router as BotRouter
from aiogram.filters import Command
from aiogram.types import BotCommand, Message, CallbackQuery, User

from rtgbot.components.base import Window, WindowsGroup
from rtgbot.etities.user_info import UserInfo
from rtgbot.message_info_storage.message_info_storage import TgMessageInfoStorage
from rtgbot.message_sender import MessageSender
from rtgbot.user_session import UserSession


class Runner:
    def __init__(self, start_screen: Window | WindowsGroup, bot_token: str,
                 message_info_storage: TgMessageInfoStorage,
                 callback_query_handlers: tp.List[tp.Callable] = [],
                 render_context_provider: tp.Callable[[UserInfo], tp.Coroutine] = None,
                 on_user_session_started: tp.Callable[[UserInfo], tp.Coroutine] = None,
                 on_user_session_stopped: tp.Callable[[UserInfo], tp.Coroutine] = None):
        self.bot = Bot(bot_token, parse_mode="HTML")
        self.dispatcher = Dispatcher()
        self.bot_router = BotRouter()

        self.start_screen = start_screen
        self.message_sender = MessageSender(self.bot, message_info_storage)
        self.callback_queue = asyncio.Queue()
        self.user_sessions: tp.Dict[int, UserSession] = {}

        self.callback_query_handlers = callback_query_handlers
        self.render_context_provider = render_context_provider
        self.on_user_session_started = on_user_session_started
        self.on_user_session_stopped = on_user_session_stopped

        @self.dispatcher.startup()
        async def _on_bot_startup():
            self.dispatcher.include_router(self.bot_router)

            await self.bot.set_my_commands(
                [
                    BotCommand(command="/start", description="🚀 Запустить бота"),
                    BotCommand(command="/refresh", description="🔄 Обновить страницу"),
                    BotCommand(command="/back", description="⬅ Назад"),
                ]
            )

        @self.bot_router.message(Command(commands=["start"]))
        async def handle_start_command(message: Message) -> None:
            if not self._check_chat_private(message):
                return

            user = message.from_user
            session, created = await self._get_user_session(UserInfo(user.id, user))
            session.navigator.reset()
            if not created:
                await session.schedule_screen_reset()
                await self._try_delete_message(message)

        @self.bot_router.message(Command(commands=["refresh"]))
        async def handle_start_command(message: Message) -> None:
            if not self._check_chat_private(message):
                return

            user = message.from_user
            (await self._get_user_session(UserInfo(user.id, user)))[0].root.invalidate()
            await self._try_delete_message(message)

        @self.bot_router.message(Command(commands=["back"]))
        async def handle_start_command(message: Message) -> None:
            if not self._check_chat_private(message):
                return

            user = message.from_user
            (await self._get_user_session(UserInfo(user.id, user)))[0].navigator.back()
            await self._try_delete_message(message)

        @self.bot_router.message()
        async def message_handler(message: Message) -> None:
            if not self._check_chat_private(message):
                return

            await asyncio.sleep(0.5)

            user = message.from_user
            (await self._get_user_session(UserInfo(user.id, user)))[0].event_processor.push_message_input(message)
            await self._try_delete_message(message)

        @self.bot_router.callback_query()
        async def handle_callback_query(callback_query: CallbackQuery):
            user = callback_query.from_user
            session, created = await self._get_user_session(UserInfo(user.id, user), start_immediately=False)
            if created:
                await session.start(display=False)

            if not session.event_processor.push_button_click(callback_query.data):
                for handler in self.callback_query_handlers:
                    if await handler(callback_query):
                        return

                await session.schedule_screen_reset()

    def start(self):
        self.message_sender.start()
        asyncio.create_task(self.dispatcher.start_polling(self.bot))

    async def stop(self):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.dispatcher.stop_polling())
            tg.create_task(self.message_sender.stop())

            for user_id in self.user_sessions.keys():
                tg.create_task(self.reset_user_session(user_id))

    async def reset_user_session(self, user_id: int):
        session, created = await self._get_user_session(UserInfo(user_id=user_id))

        if not created:
            session.navigator.reset()

        await session.stop()
        self.user_sessions.pop(user_id)

        if self.on_user_session_stopped:
            await self.on_user_session_stopped(session.user_info)

    async def _get_user_session(self, user_info: UserInfo, start_immediately=True):
        user_id = user_info.user_id

        try:
            session = self.user_sessions[user_id]
            session.update_user_info(user_info)

            return session, False
        except KeyError:
            session = UserSession(self.bot, user_info, copy.deepcopy(self.start_screen), self.message_sender,
                                  self.render_context_provider, self.on_user_session_started)
            if start_immediately:
                await session.start()
            self.user_sessions[user_id] = session

            return session, True

    async def _try_delete_message(self, message):
        try:
            await message.delete()
        except Exception:
            pass

    def _check_chat_private(self, message: Message):
        return message.chat.type == "private"
