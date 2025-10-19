import time
from dataclasses import dataclass
from typing import Any, List


@dataclass
class Fragment:
    user_id: str
    display_name: str
    message: str
    timestamp: float

@dataclass
class HistoryData:
    user_messages: List[Fragment]
    image_path: str
    is_multimodal: bool
    ai_response: str
    response_time: float
