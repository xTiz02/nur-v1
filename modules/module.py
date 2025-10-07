import asyncio
from modules.injection import Injection

'''
Una clase extensible que define un módulo que interactúa con el programa principal.
Todos los módulos se ejecutarán en su propio hilo con su propio bucle de eventos.
No utilice esta clase directamente, extiéndala.
'''

class Module:

    def __init__(self, signals, enabled=True):
        self.signals = signals
        self.enabled = enabled

        self.prompt_injection = Injection("", -1)

    def init_event_loop(self):
        asyncio.run(self.run())

    def get_prompt_injection(self):
        return self.prompt_injection

    # Funcion que se llama después de que todos los módulos hayan proporcionado sus inyecciones
    def cleanup(self):
        pass

    async def run(self):
        pass