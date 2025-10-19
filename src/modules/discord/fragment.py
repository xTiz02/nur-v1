import time
from typing import Any

from src.com.model.models import Fragment

'''
Esta clase es responsable de gestionar los fragmentos de mensajes recibidos de los usuarios.
Por cualquier interfaz (Discord, Twitch, etc.), mientras sea texto.
'''
class FragmentManager:
    def __init__(self, signals):
        # Mensajes normales y pendientes
        self._current_messages: list[Fragment] = []
        self._pending_messages: list[Fragment] = []
        # Historial total (todos los mensajes)
        self._all_messages: list[Fragment] = []
        self.signals = signals

    def process_fragment(self, user, fragment: str):
        """Guarda cada fragmento de usuario en su lista correspondiente"""
        message_data = Fragment(
            user_id=user.id,
            display_name=user.display_name,
            message=fragment,timestamp=time.time())

        if self.signals.AI_speaking or self.signals.AI_thinking:
            print(f"[DEBUG] IA hablando/pensando. Guardando pendiente: {fragment}")
            self._pending_messages.append(message_data)
        else:
            print(f"[DEBUG] Agregando mensaje actual de {message_data.display_name}: {fragment}")
            self._current_messages.append(message_data)
            self.signals.new_message = True

        # Registrar en el historial general
        self._all_messages.append(message_data)

    def get_full_fragments(self) -> dict[str, list[Fragment]]:
        """Retorna los fragmentos actuales y pendientes ordenados por timestamp (descendente)"""
        def sort_by_time(messages: list[Fragment]) -> list[Fragment]:
            return sorted(messages, key=lambda x: x.timestamp, reverse=False)

        return {
            "pending": sort_by_time(self._pending_messages),
            "current": sort_by_time(self._current_messages)
        }

    def get_last_message(self) -> Fragment | None:
        """Retorna el último mensaje recibido (de cualquier usuario o estado)"""
        if not self._all_messages:
            return None
        # El más reciente por timestamp
        return max(self._all_messages, key=lambda x: x.timestamp)

    def clear_buffers(self):
        """Limpia todas las listas"""
        self._current_messages.clear()
        self._pending_messages.clear()
        self._all_messages.clear()

    @property
    def all_messages(self):
        """Retorna el historial"""
        return self._all_messages

    @property
    def pending_messages(self):
        return self._pending_messages

    @property
    def current_messages(self):
        return self._current_messages
