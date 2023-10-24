import asyncio
import logging
import time
import typing as tp
from dataclasses import dataclass

from aiogram.types import Message

import rtgbot.base
from rtgbot.etities.dom import DOM, ButtonElement, InputElement, MessageElement
from rtgbot.etities.event import Event, CustomEvent, MessageInputEvent, ButtonClickEvent
from rtgbot.utils import unpack_kbd_buttons


class EventProcessor:
    @dataclass
    class NodeModification:
        node: rtgbot.base.ComponentTreeNode

    def __init__(self, on_event_processed: tp.Callable):
        self.event_queue = asyncio.Queue()
        self.on_event_processed = on_event_processed

        self.button_elements: tp.Dict[str, ButtonElement] = {}
        self.input_elements: tp.List[InputElement] = []

    def start(self):
        self._event_handler_task = asyncio.create_task(self._event_handler())

    async def stop(self):
        try:
            await self.event_queue.join()
            self._event_handler_task.cancel()
        except AttributeError:
            pass

    def push_button_click(self, button_id: str):
        try:
            button_element = self.button_elements[button_id]
            button_node = button_element.tree_node

            event = ButtonClickEvent(sender=button_node, dom_element=button_element)
            self.event_queue.put_nowait(event)
            return True
        except KeyError:
            logging.warning("invalid button id")
            return False

    def push_message_input(self, message: Message):
        for input_element in self.input_elements:
            input_node = input_element.tree_node

            event = MessageInputEvent(sender=input_node, dom_element=input_element, tg_message=message)
            self.event_queue.put_nowait(event)
            return True
        return False

    def push_custom_event(self, sender: rtgbot.base.ComponentTreeNode, name: str, data: tp.Dict = None):
        if data is None:
            data = {}

        event = CustomEvent(sender=sender, name=name, data=data)
        self.event_queue.put_nowait(event)

    def push_node_modification(self, node: rtgbot.base.ComponentTreeNode):
        self.event_queue.put_nowait(self.NodeModification(node))

    def register_dom_callbacks(self, dom: DOM):
        self.button_elements.clear()
        self.input_elements.clear()

        for message in dom:
            for button_el in unpack_kbd_buttons(message.keyboard):
                self.button_elements[button_el.button_id] = button_el
            for input_el in message.inputs:
                self.input_elements.append(input_el)

    async def _event_handler(self):
        event_counter = 0

        while True:
            event = await self.event_queue.get()

            modified_nodes = set()
            force_update_node = None

            start = time.time()

            while True:
                if isinstance(event, self.NodeModification):
                    node = event.node
                    if node not in modified_nodes:
                        if node.rct._reset_state_history() or node._is_dirty:
                            modified_nodes.add(node)
                        node._is_dirty = False
                else:
                    event: Event = event

                    if isinstance(event, ButtonClickEvent):
                        force_update_node = event.sender
                        modified_nodes.add(force_update_node)

                    logging.info(f"handle event {event_counter}: {event}")
                    event_counter += 1

                    await self._propagate_event(event)

                if self.event_queue.empty():
                    break

                self.event_queue.task_done()
                event = await self.event_queue.get()

            end = time.time()
            logging.info(f"event handling time: {end - start}")

            # trigger re-render
            await self.on_event_processed(event, modified_nodes, force_update_node)
            self.event_queue.task_done()

    async def _propagate_event(self, event: Event):
        node = event.sender

        while node and event.should_propagate:
            try:
                await node.on_event(event)
            except Exception:
                logging.exception(f"Exception occurred while processing event:")

            node = node._render_data.parent
