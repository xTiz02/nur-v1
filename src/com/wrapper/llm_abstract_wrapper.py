import copy
import json
import time
from abc import abstractmethod
from typing import List

from env import MODEL_NAME
from src.com.model.models import Fragment
from src.com.wrapper.llm_state import LLMState
from src.modules.llm.llm_interface import LLMInterface
from utils.constans import *
import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold, GenerationConfig
import env
from src.injection import Injection


class AbstractLLMWrapper:

    def __init__(self, signals, tts, llm_state: LLMState,agent:LLMInterface, modules=None):
        self.signals = signals
        self.llm_state = llm_state
        self.agent = agent

        self.tts = tts
        self.API = self.API(self)
        if modules is None:
            self.modules = {}
        else:
            self.modules = modules
        #Below constants must be set by child classes
        # Constantes deben ser establecidas por las clases hijas
        # self.CONTEXT_SIZE = None
        # self.tokenizer = None
    # Filtro de lista negra simple
    def is_filtered(self, text):
        # Filtra si el mensaje contiene una palabra en la lista negra
        if any(bad_word.lower() in text.lower().split() for bad_word in self.llm_state.blacklist):
            return True
        else:
            return False

    # Obtiene todas las inyecciones de todos los módulos y las ensambla en un solo prompt por prioridad creciente
    def assemble_injections(self, injections=None):
        if injections is None:
            injections = []

        for module in self.modules.values():
            injections.append(module.get_prompt_injection())

        # Limpia todos los módulos una vez que se ha obtenido la inyección de prompt de todos los módulos
        for module in self.modules.values():
            module.cleanup()

        # Ordenar inyecciones por prioridad
        injections = sorted(injections, key=lambda x: x.priority)

        # Ensambla el prompt final
        prompt = ""
        for injection in injections:
            prompt += injection.text
        return prompt

    def generate_prompt(self):
        # De momento solo generamos el prompt si hay un nuevo mensaje del usuario
        if self.signals.new_message:
            # Obtener copia profunda del ultimo historial de mensajes
            messages = copy.deepcopy(self.signals.history[-1])

            chat_section = ""
            pending_chat_section = ""
            list_pending : List[Fragment] = messages["pending"]
            list_current: List[Fragment] = messages["current"]
            if len(list_pending) > 0:
                for fragment in list_pending :
                    pending_chat_section += fragment.display_name + ": " + fragment.message + "\n"
            if len(list_current) > 0:
                for fragment in list_current:
                    chat_section += fragment.display_name + ": " + fragment.message + "\n"

            generation_prompt = AI_NAME + ": "

            base_injections = [ Injection(chat_section, 100), Injection(pending_chat_section, 110)]
            full_prompt = self.assemble_injections(base_injections) + generation_prompt

            self.signals.sio_queue.put(("full_prompt", full_prompt))
            print(f"FULL PROMPT:\n{full_prompt}\n---END OF PROMPT---")
            return full_prompt

    @abstractmethod
    def prepare_payload(self):
        raise NotImplementedError("Must implement prepare_payload in child classes")

    def prompt(self):
        if not self.llm_state.enabled:
            return

        self.signals.AI_thinking = True
        data = None
        if self.signals.new_message:
            data = self.prepare_payload()
        else:
            # Si se llego aqui algo salio mal, no deberia llegar aqui sin input nuevo
            print("No new message to process.")
            # data = self.default_prompt()
            return
        self.signals.new_message = False
        self.signals.sio_queue.put(("reset_next_message", None))

        self.agent.chat(data)

        AI_message = ''
        # Aqui hacer cambios para llamar a al metodo de chat de agente y obtener el stream  de datos de respuesta.
        # for event in response_stream.events():
        #     # Check to see if next message was canceled
        #     if self.llm_state.next_cancelled:
        #         print(f"Chunk de texto cancelado.")
        #         continue
        #
        #     payload = json.loads(event.data)
        #     chunk = payload['choices'][0]['delta']['content']
        #     AI_message += chunk
        #     self.signals.sio_queue.put(("next_chunk", chunk))
        #
        # if self.llm_state.next_cancelled:
        #     self.llm_state.next_cancelled = False
        #     self.signals.sio_queue.put(("reset_next_message", None))
        #     self.signals.AI_thinking = False
        #     return

        print("AI OUTPUT: " + AI_message)
        self.signals.last_message_time = time.time()
        self.signals.AI_speaking = False
        self.signals.AI_thinking = False

        if self.is_filtered(AI_message):
            AI_message = "Sin comentarios ..."
            self.signals.sio_queue.put(("reset_next_message", None))
            self.signals.sio_queue.put(("next_chunk", AI_message))

        # self.signals.history.append({"role": "assistant", "content": AI_message})
        # self.tts.play(AI_message)

    class API:
        def __init__(self, outer):
            self.outer = outer

        def get_blacklist(self):
            return self.outer.llm_state.blacklist

        def set_blacklist(self, new_blacklist):
            self.outer.llm_state.blacklist = new_blacklist
            with open('blacklist.txt', 'w') as file:
                for word in new_blacklist:
                    file.write(word + "\n")

            # Notify clients
            self.outer.signals.sio_queue.put(('get_blacklist', new_blacklist))

        def set_LLM_status(self, status):
            self.outer.llm_state.enabled = status
            if status:
                self.outer.signals.AI_thinking = False
            self.outer.signals.sio_queue.put(('LLM_status', status))

        def get_LLM_status(self):
            return self.outer.llm_state.enabled

        def cancel_next(self):
            self.outer.llm_state.next_cancelled = True
            # For text-generation-webui: Immediately stop generation
            # requests.post(self.outer.LLM_ENDPOINT + "/v1/internal/stop-generation", headers={"Content-Type": "application/json"})