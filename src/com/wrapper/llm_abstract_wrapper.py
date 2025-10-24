import copy
import time
from abc import abstractmethod
from typing import List
from env import MODEL_NAME
from src.com.model.models import Fragment
from src.com.wrapper.llm_state import LLMState
from src.modules.llm.llm_interface import LLMInterface
from src.modules.tts.tts_google import GoogleTTSEngine
from utils.constans import *
import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold, GenerationConfig
import env
from src.injection import Injection

class AbstractLLMWrapper:

    def __init__(self, signals, tts:GoogleTTSEngine, llm_state: LLMState,agent:LLMInterface, modules=None):
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
        """
        Método principal - TODO EN ESTE HILO (Prompter).
        1. Obtiene respuesta COMPLETA del LLM (blocking)
        2. Envía a TTS que genera chunks de audio (blocking generator)
        3. Cada chunk va a la cola para el bot
        """
        if not self.llm_state.enabled:
            return

        self.signals.AI_thinking = True

        # Preparar datos
        if self.signals.new_message:
            prompt_data = self.prepare_payload()
        else:
            print("No new message to process")
            return

        self.signals.new_message = False
        self.signals.sio_queue.put(("reset_next_message", None))

        try:
            # PASO 1: Obtener respuesta COMPLETA del LLM (blocking)
            print("Solicitando respuesta al LLM...")
            full_text = self.agent.chat(prompt_data)  # ← Retorna STRING directamente

            # Verificar cancelación
            if self.llm_state.next_cancelled:
                print("Generación cancelada")
                self.llm_state.next_cancelled = False
                self.signals.AI_thinking = False
                return

            print(f"Respuesta recibida: {len(full_text)} caracteres")
            print(f"Texto: '{full_text}...'")

            # Filtrado
            if self.is_filtered(full_text):
                full_text = "Sin comentarios..."
                print("Respuesta filtrada por lista negra")

            # Guardar en historial
            self.signals.history.append({"role": "assistant", "content": full_text})

            # Enviar a UI
            # self.signals.sio_queue.put(("next_chunk", full_text))

            # PASO 2: Enviar texto completo al TTS (blocking generator)
            print("Enviando texto al TTS...")
            self.signals.AI_thinking = False  # Ya no está pensando

            # TTS retorna un generator de chunks de audio
            audio_chunk = self.tts.synthesize_full(full_text,save_path=".demos/temp/"+ str(time.time()) +".wav")

            if self.llm_state.next_cancelled:
                print("TTS cancelado")
                return
            self.signals.audio_ready = True
            self.signals.audio_queue.put(audio_chunk)
            print("Primer chunk de audio disponible para el bot")

        except Exception as e:
            print(f"Error durante prompt(): {e}")

        finally:
            self.signals.AI_thinking = False
            self.signals.last_message_time = time.time()

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