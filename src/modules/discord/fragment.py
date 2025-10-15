from typing import Any, List

from src.com.model.models import UserMessages, Fragment


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
            print(f"[DEBUG] Agregando fragmento al buffer del usuario {user.display_name}: {fragment}")
            user_id = user.id
            if user_id not in self._user_buffers:
                self._user_buffers[user_id] = UserMessages(user=user, fragments=[])
            self._user_buffers[user_id].fragments.append(Fragment(text=fragment))

    def get_full_fragments(self) -> dict[str, List[str]]:
        """Retorna y limpia todos los buffers de usuarios y pendientes"""
        full_fragments = {}
        for user_id in list(self._pending_fragment.keys()):
            pending_frags = self._flush_pending_buffers(user_id)
            if pending_frags:
                full_fragments.update(pending_frags)
        for user_id in list(self._user_buffers.keys()):
            user_frags = self._flush_user_buffer(user_id)
            if user_frags:
                full_fragments.update(user_frags)
        return full_fragments

    def _flush_user_buffer(self, user_id) -> dict[str, List[str]]:
        """Retorna cada fragmento del usuario como elementos separados en una lista"""
        if user_id not in self._user_buffers or not self._user_buffers[user_id].fragments:
            return {}
        user_name = self._user_buffers[user_id].user.display_name
        print(f"[DEBUG] Agregando fragmentos del usuario {user_name} al historial")
        fragments = [frag.text for frag in self._user_buffers[user_id].fragments]
        return {user_name: fragments}

    def _flush_pending_buffers(self,user_id) -> dict[str, List[str]]:
        """Retorna cada fragmento pendiente del usuario como elementos separados en una lista"""
        if user_id in self._pending_fragment or not self._pending_fragment[user_id].fragments:
            return {}
        user_name = self._pending_fragment[user_id].user.display_name
        print(f"[DEBUG] Agregando fragmentos pendientes para usuario {user_name}")
        pending_frags = [frag.text for frag in self._pending_fragment[user_id].fragments]
        return {user_name: pending_frags}

    def clear_buffers(self):
        """Limpia todos los buffers de usuarios y pendientes"""
        self._user_buffers = {}
        self._pending_fragment = {}

    @property
    def get_user_buffers(self):
        return self._user_buffers

    @property
    def get_pending_buffers(self):
        return self._pending_fragment


