import time
from dataclasses import dataclass
from typing import Any, List


@dataclass
class Fragment:
    text: str
    timestamp: float = time.time()

@dataclass
class UserMessages:
    user: Any
    fragments: List[Fragment]

@dataclass
class HistoryData:
    user_messages: List[UserMessages]
    image_path: str
    is_multimodal: bool
    ai_response: str
    response_time: float
