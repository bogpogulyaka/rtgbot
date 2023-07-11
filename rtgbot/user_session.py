import logging
import time
import typing as tp

import aiogram

from rtgbot.base import ComponentTreeNode
from rtgbot.components.navigation_stack import NavigationStack
from rtgbot.etities.dom import RenderContext
from rtgbot.etities.event import Event
from rtgbot.etities.user_info import UserInfo
from rtgbot.event_processor import EventProcessor
from rtgbot.message_sender import MessageSender
from rtgbot.renderer import Renderer
from rtgbot.navigator import Navigator


class UserSession:
    def __init__(self, bot: aiogram.Bot,
                 user_info: UserInfo, start_screen, message_sender: MessageSender,
                 render_context_provider: tp.Callable[[UserInfo], tp.Coroutine] = None,
                 on_started: tp.Callable[[UserInfo], tp.Coroutine] = None):
        self.user_info = user_info
        self.render_context_provider = render_context_provider
        self.on_started = on_started

        self.root = NavigationStack()

        self.navigator = Navigator(self.root, start_screen)
        self.event_processor = EventProcessor(on_event_processed=self._on_event_processed)
        self.context = RenderContext(
            bot=bot,
            user_id=user_info.user_id,
            navigator=self.navigator,
            event_manager=self.event_processor
        )

        self.renderer = Renderer(self.context)
        self.message_sender = message_sender

        self._is_started = False

    async def start(self, display=True):
        if self._is_started:
            # logging.warning("Session is already started!")
            return
        self._is_started = True

        if self.on_started:
            await self.on_started(self.user_info)

        await self._update_render_context()

        dom, dom_update = await self.renderer.render([self.root])
        if display:
            self.message_sender.schedule_screen_reset(self.user_info.user_id, dom)

        self.event_processor.register_dom_callbacks(dom)
        self.event_processor.start()

    async def stop(self):
        await self.event_processor.stop()

    async def schedule_screen_reset(self):
        await self._update_render_context()
        dom, dom_update = await self.renderer.render([self.root])
        self.message_sender.schedule_screen_reset(self.user_info.user_id, dom)

    @property
    def is_started(self):
        return self._is_started

    def update_user_info(self, user_info: UserInfo):
        self.user_info = user_info

    async def _on_event_processed(self, event: Event, modified_nodes: tp.List[ComponentTreeNode], force_update_node: ComponentTreeNode):
        # logging.info(modified_nodes)

        if len(modified_nodes) == 0:
            return

        await self._update_render_context()

        start = time.time()

        dom, dom_update = await self.renderer.render(modified_nodes, force_update_node)
        self.event_processor.register_dom_callbacks(dom)

        end = time.time()
        logging.info(f"rendering time: {end - start}")

        self.message_sender.schedule_screen_update(self.user_info.user_id, dom, dom_update)

    async def _update_render_context(self):
        if self.render_context_provider:
            try:
                data = await self.render_context_provider(self.user_info)
                for k, v in data.items():
                    setattr(self.context, k, v)
            except Exception:
                logging.exception(f"Exception in context provider:")
