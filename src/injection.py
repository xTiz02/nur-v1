
'''
Representa el texto que se inyectará en el mensaje de LLM.
Las inyecciones se añaden al mensaje de menor a mayor prioridad, siendo la más alta la última.
"Texto" es el texto que se inyectará.
La prioridad es un número entero positivo. Las inyecciones con prioridad negativa se ignorarán.
Prioridad del mensaje del sistema: 10
Historial de mensajes: 50
'''


class Injection:
    def __init__(self, text, priority, title=""):
        self.text = text
        self.priority = priority
        self.title = title

    def __str__(self):
        return self.text