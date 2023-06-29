import asyncio
import logging
import time
import typing as tp
from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto

from rtgbot.etities.dom import DOM, DOMUpdate, MessageElement, DOMMessageUpdate
from rtgbot.etities.message_info import TgMessageInfo
from rtgbot.message_info_storage.message_info_storage import TgMessageInfoStorage
from rtgbot.utils import Symbols, cond_kw


@dataclass
class TgMessageData:
    media: str
    text: str
    inline_keyboard: tp.List
    disable_web_page_preview: bool
    disable_notification: bool
    parse_mode: str


class MessageSender:
    def __init__(self, bot: Bot, message_info_storage: TgMessageInfoStorage):
        self.bot = bot
        self.task_queue = asyncio.Queue()

        self.message_info_storage = message_info_storage
        self.default_image_url = 'https://liftlearning.com/wp-content/uploads/2020/09/default-image.png'

    def start(self):
        self._task_handler_task = asyncio.create_task(self._task_handler())

    async def stop(self):
        try:
            await self.task_queue.join()
            self._task_handler_task.cancel()
        except:
            pass

    def schedule_screen_reset(self, chat_id: int, dom: DOM):
        # logging.info("schedule reset")
        self.task_queue.put_nowait(self._reset_screen(chat_id, dom))

    def schedule_screen_update(self, chat_id: int, dom: DOM, dom_update: DOMUpdate):
        # logging.info("schedule update")
        self.task_queue.put_nowait(self._update_screen(chat_id, dom, dom_update))

    async def _task_handler(self):
        while True:
            task = await self.task_queue.get()
            await task
            self.task_queue.task_done()

    async def _reset_screen(self, chat_id: int, dom: DOM):
        # logging.info(f"reset screen, chat_id: {chat_id}")

        async def send_messages():
            for message in dom:
                await self._send_message(chat_id, message)

        sent_messages = await self.message_info_storage.get_all(chat_id)
        await self.message_info_storage.remove_all(chat_id)

        tasks = []

        tasks.append(send_messages())
        for message in sent_messages:
            tasks.append(self._delete_message_by_id(chat_id, message.message_id))

        for task in asyncio.as_completed(tasks):
            try:
                await task
            except:
                logging.exception("Exception in message sender:")

    async def _update_screen(self, chat_id: int, dom: DOM, dom_update: DOMUpdate):
        # logging.info(f"update screen, chat_id: {chat_id}")

        async def send_messages():
            for update in dom_update:
                if update.action == DOMMessageUpdate.Action.send:
                    await self._send_message(chat_id, update.new_message)

        start = time.time()

        tasks = []

        tasks.append(send_messages())

        for update in dom_update:
            if update.action == DOMMessageUpdate.Action.keep or update.action == DOMMessageUpdate.Action.update:
                tasks.append(self._update_message(chat_id, update))
            elif update.action == DOMMessageUpdate.Action.delete:
                tasks.append(self._delete_message(chat_id, update.old_message.key))

        failed = False

        for task in asyncio.as_completed(tasks):
            try:
                await task
            except:
                failed = True
                logging.exception("Exception in message sender:")

        if failed:
            await self._reset_screen(chat_id, dom)

        end = time.time()
        logging.info(f"screen update time: {end - start}")

    def _prepare_message_data(self, message: MessageElement, update_counter: int):
        media = None
        if len(message.media) > 0:
            url = message.media[0].url
            media = url != "" and url or self.default_image_url

        text = message.text
        if text == '':
            text = Symbols.EMPTY2 + ' ' * 55 + Symbols.ZW  # ⠛
        if update_counter % 2 == 1:
            text = Symbols.ZW + text

        inline_keyboard = []
        for row in message.keyboard:
            line = []
            for button in row:
                line.append(InlineKeyboardButton(
                    text=button.text,
                    **cond_kw(button.url != '', url=button.url),
                    callback_data=button.button_id
                ))
            inline_keyboard.append(line)

        return TgMessageData(
            media=media,
            text=text,
            inline_keyboard=inline_keyboard,
            parse_mode=message.parse_mode,
            disable_web_page_preview=message.disable_web_page_preview,
            disable_notification=not message.enable_notification
        )

    async def _send_message(self, chat_id: int, message: MessageElement):
        message_data = self._prepare_message_data(message, 0)

        if not message_data.media:
            result_message = await self.bot.send_message(
                chat_id=chat_id,
                text=message_data.text,
                parse_mode=message_data.parse_mode,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=message_data.inline_keyboard
                ),
                disable_web_page_preview=message_data.disable_web_page_preview,
                disable_notification=message_data.disable_notification
            )
        else:
            result_message = await self.bot.send_photo(
                chat_id=chat_id,
                photo=message_data.media,
                caption=message_data.text,
                parse_mode=message_data.parse_mode,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=message_data.inline_keyboard
                ),
                disable_notification=message_data.disable_notification
            )

        await self.message_info_storage.add(chat_id, message.key,
                                            TgMessageInfo(result_message.message_id, message_data.media is not None))

    async def _update_message(self, chat_id: int, update: DOMMessageUpdate):
        message_info: TgMessageInfo = await self.message_info_storage.get(chat_id, update.old_message.key)

        if update.action == DOMMessageUpdate.Action.update:
            message_id = message_info.message_id
            has_media = message_info.has_media

            old_message = update.old_message
            message = update.new_message

            diff_media = not message.compare_media(old_message)
            diff_text = not message.compare_text(old_message)
            diff_kbd = not message.compare_kbd(old_message)

            if not diff_media and not diff_text and not diff_kbd:
                message_info.update_counter += 1
                diff_text = True

            message_data = self._prepare_message_data(message, message_info.update_counter)
            if has_media and message_data.media is None:
                message_data.media = self.default_image_url

            if diff_media:
                await self.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=InputMediaPhoto(
                        media=message_data.media,
                        caption=message_data.text
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=message_data.inline_keyboard
                    ),
                )
            elif diff_text:
                if not has_media:
                    await self.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=message_data.text,
                        parse_mode=message_data.parse_mode,
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=message_data.inline_keyboard
                        ),
                        disable_web_page_preview=message_data.disable_web_page_preview
                    )
                else:
                    await self.bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=message_id,
                        caption=message_data.text,
                        parse_mode=message_data.parse_mode,
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=message_data.inline_keyboard
                        ),
                    )
            elif diff_kbd:
                await self.bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=message_data.inline_keyboard
                    )
                )

        await self.message_info_storage.remove(chat_id, message_info.message_id)
        await self.message_info_storage.add(chat_id, update.new_message.key, message_info)

    async def _delete_message(self, chat_id: int, message_key: str):
        message_info = await self.message_info_storage.get(chat_id, message_key)
        await self._delete_message_by_id(chat_id, message_info.message_id)
        await self.message_info_storage.remove(chat_id, message_info.message_id)

    async def _delete_message_by_id(self, chat_id: int, message_id: int):
        await self.bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
        )

