class FragmentManager:
    def __init__(self, signals):
        self._user_buffers = {}  # Diccionario para almacenar dialogo por usuario
        # self._user_timers = {}
        self.signals = signals
        self._pending_fragment = {}  # Dialogo que llega mientras habla la IA

    def process_fragment(self, user, fragment: str):
        """Agrega fragmento al buffer del usuario o lo guarda en pendiente si la IA está hablando"""
        if self.signals.AI_speaking:
            print(f"[DEBUG] IA hablando, guardando en buffer pendiente: {fragment}")
            user_id = user.id
            if user_id not in self._pending_fragment:
                self._pending_fragment[user_id] = {
                    'user': user,
                    'fragments': []
                }
            self._pending_fragment[user_id]['fragments'].append(fragment)
        else:
            self.add_fragment(user, fragment)

    def add_fragment(self, user, text: str):
        """Agrega fragmento al buffer del usuario"""
        user_id = user.id

        # Acumular en buffer
        if user_id not in self._user_buffers:
            self._user_buffers[user_id] = []
        self._user_buffers[user_id].append(text)
