import time

from src.modules.discord.fragment import FragmentManager
from utils.constans import PATIENCE


class Prompter:
    def __init__(self, signals, llms,manager:FragmentManager, modules=None):
        self.signals = signals
        self.llms = llms
        self.manager = manager
        if modules is None:
            self.modules = {}
        else:
            self.modules = modules

        self.system_ready = False
        self.timeSinceLastMessage = 0.0

    def prompt_now(self):
        if not self.signals.tts_ready and self.signals.new_message:
            return True
        # No generar prompts si el sistema no está listo
        # if not self.signals.stt_ready or not self.signals.tts_ready:
        #     return False
        # No generar prompts si alguien ya está hablando o la IA está pensando/hablando
        if self.signals.process_text or self.signals.human_speaking or self.signals.AI_thinking or self.signals.AI_speaking:
            return False
        # # Prompt AI if there are unprocessed chat messages
        # if len(self.signals.recentTwitchMessages) > 0:
        #     return True
        # Prompt if some amount of seconds has passed without anyone talking
        if self.timeSinceLastMessage > PATIENCE:
            return True

    def choose_llm(self):
        if "multimodal" in self.modules and self.modules["multimodal"].API.multimodal_now():
            print(f"Choosing IMAGE LLM")
            return self.llms["image"]
        else:
            print(f"Choosing TEXT LLM")
            return self.llms["text"]

    def prompt_loop(self):
        print("Prompter loop started")

        while not self.signals.terminate:
            if not self.signals.human_speaking:
                time.sleep(1)

            current_time = time.time()
            if self.signals.tts_ready:
                # Setear el tiempo del último mensaje si es 0 o si el sistema no está listo
                if self.signals.last_message_time == 0.0 or (not self.signals.stt_ready or not self.signals.tts_ready):
                    # self.signals.last_message_time = time.time()
                    self.timeSinceLastMessage = 0.0
                else:
                    if not self.system_ready:
                        print("SYSTEM READY")
                        self.system_ready = True
                # Calcular el tiempo desde el último mensaje
                if self.signals.new_message:
                    last_fragment = self.manager.get_last_message()
                    self.timeSinceLastMessage = current_time - last_fragment.timestamp
                self.signals.sio_queue.put(("patience_update", {"crr_time": self.timeSinceLastMessage, "total_time": PATIENCE}))

            # Decide and prompt LLM
            # print("Checking if should prompt LLM...")
            if self.prompt_now():
                print("PROMPTING AI")
                if self.signals.new_message:
                    full_fragments = self.manager.get_full_fragments()
                    # enviar fragments a history
                    self.signals.history.append(full_fragments)
                    self.manager.clear_buffers()
                    print(f"[DEBUG] Fragmentos finales completos enviados al historial: {self.signals.history}")

                llm_wrapper = self.choose_llm()
                llm_wrapper.prompt()

                self.signals.new_message = False