from dataclasses import dataclass


@dataclass
class TgMessageInfo:
    message_id: int
    has_media: bool
    update_counter: int = 0
