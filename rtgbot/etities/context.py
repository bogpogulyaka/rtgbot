import typing as tp
from dataclasses import dataclass

import aiogram


@dataclass
class RenderContext:
    bot: aiogram.Bot
    user_id: int
    navigator: tp.Any
    event_manager: tp.Any
    render_cycle_id: int = 0
    is_banned: bool = False
