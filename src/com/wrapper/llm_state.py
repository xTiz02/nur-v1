"""
Una clase que controla si se cancela la respuesta de la ia o no,
y maneja una lista negra de palabras.
"""
class LLMState:
    def __init__(self):
        self.enabled = True
        self.next_cancelled = False

        # Lee la lista negra desde un archivo de texto
        with open('blacklist.txt', 'r') as file:
            self.blacklist = file.read().splitlines()