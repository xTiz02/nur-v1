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
    fragments: List[Fragment] = None

class FragmentManager:
    def __init__(self, signals):
        self._user_buffers: dict[Any, UserMessages] = {}  # Diccionario para almacenar dialogo por usuario
        # self._user_timers = {}
        self.signals = signals
        self._pending_fragment: dict[Any, UserMessages] = {}  # Dialogo que llega mientras habla la IA

    def process_fragment(self, user, fragment: str):
        """Agrega fragmento al buffer del usuario o lo guarda en pendiente si la IA está hablando"""
        if self.signals.AI_speaking or self.signals.AI_thinking:
            print(f"[DEBUG] IA hablando O pensando, guardando en buffer pendiente: {fragment}")
            user_id = user.id
            if user_id not in self._pending_fragment:
                self._pending_fragment[user_id] = UserMessages(user=user, fragments=[])
            self._pending_fragment[user_id].fragments.append(Fragment(text=fragment))
        else:
            self.add_fragment(user, fragment)

    def add_fragment(self, user, text: str):
        """Agrega fragmento al buffer del usuario"""
        user_id = user.id

        # Acumular en buffer
        if user_id not in self._user_buffers:
            self._user_buffers[user_id] = UserMessages(user=user, fragments=[])
        self._user_buffers[user_id].fragments.append(Fragment(text=text))
