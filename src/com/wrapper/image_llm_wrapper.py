import os
import time

import mss, cv2, base64
import numpy as np
from vertexai.generative_models import Part, Image

from utils.constans import *

from src.com.wrapper.llm_abstract_wrapper import AbstractLLMWrapper
from src.modules.llm.llm_interface import LLMInterface


class ImageLLMWrapper(AbstractLLMWrapper):

    def __init__(self, signals, tts, llmState,agent: LLMInterface, modules=None):
        super().__init__(signals, tts, llmState,agent, modules)
        self.MSS = None

    def screen_shot(self) -> bytes:
        if self.MSS is None:
            self.MSS = mss.mss()

        # Tomar captura de pantalla de la pantalla primaria
        frame_bytes = self.MSS.grab(self.MSS.monitors[PRIMARY_MONITOR])

        frame_array = np.array(frame_bytes)
        # reajustar tamaño
        frame_resized = cv2.resize(frame_array, (1920, 1080), interpolation=cv2.INTER_CUBIC)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
        result, frame_encoded = cv2.imencode('.jpg', frame_resized, encode_param)
        # base64
        frame_base64 = base64.b64encode(frame_encoded).decode("utf-8")
        # guardar imagen en una capeta temporal
        path_uri = "demos/temp"
        if not os.path.exists(path_uri):
            os.makedirs(path_uri)
        name = str(int(time.time())) + ".jpg"
        with open(os.path.join(path_uri, name), "wb") as f:
            f.write(base64.b64decode(frame_base64))

        print(f"[INFO] Captura de pantalla guardada en {os.path.join('temp', name)}")
        return frame_encoded.tobytes()

    def prepare_payload(self):
        try:
            image = Part.from_image(Image.from_bytes(self.screen_shot()))
            return [
                image,
                self.generate_prompt()
            ]
        except Exception as e:
            print(f"[IMAGE LLM ERROR] prepare_payload: {e}")
            return [
                self.generate_prompt()
            ]

