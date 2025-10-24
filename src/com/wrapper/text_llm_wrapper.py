import os

from src.modules.llm.llm_interface import LLMInterface

from src.com.wrapper.llm_abstract_wrapper import AbstractLLMWrapper


class TextLLMWrapper(AbstractLLMWrapper):

    def __init__(self, signals, tts, llmState,agent: LLMInterface, modules=None):
        super().__init__(signals, tts, llmState,agent, modules)
        # self.CONTEXT_SIZE = CONTEXT_SIZE
        # self.tokenizer = AutoTokenizer.from_pretrained(MODEL, token=os.getenv("HF_TOKEN"))

    def prepare_payload(self):

        return self.generate_prompt()