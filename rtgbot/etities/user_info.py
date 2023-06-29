from dataclasses import dataclass

import aiogram.types
import typing as tp


@dataclass
class UserInfo:
    user_id: int
    user: tp.Optional[aiogram.types.User] = None
