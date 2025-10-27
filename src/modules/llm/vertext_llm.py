from typing import List

import vertexai
from google.genai.types import Content
from vertexai.generative_models import GenerativeModel, GenerationConfig, ChatSession, HarmCategory, HarmBlockThreshold

from src.modules.llm.llm_interface import LLMInterface
from utils.constans import *
import env

class VertexAgentEngine(LLMInterface):
    def __init__(
            self,
            system_instruction: str = None,
            model_name: str = env.MODEL_NAME,
            temperature: float = 0.7,
            max_output_tokens: int = 5000,
            enabled_session = False,
    ):
        """
        Inicializa un agente con sesión persistente en VertexAI.

        Args:
            system_instruction (str): instrucción del sistema para el modelo
            model_name (str): nombre del modelo de VertexAI
            temperature (float): creatividad de la respuesta
            max_output_tokens (int): longitud máxima de salida
        """
        self.project_id = env.PROJECT_ID
        self.location = env.REGION

        # Inicializa Vertex
        vertexai.init(project=self.project_id, location=self.location)

        # Configuración de seguridad más permisiva
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }

        # Configura modelo y sesión de chat
        self.model = GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            generation_config=GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
            safety_settings=self.safety_settings
        )

        # Sesión persistente (recuerda contexto) con validación deshabilitada
        if enabled_session:
            self.chatSession: ChatSession = self.model.start_chat(
                response_validation=False
            )


    def chat(self, prompt: str | List[Content]) -> str:
        """
        Retorna respuesta COMPLETA como string (sin streaming).

        Args:
            prompt: Texto del prompt

        Returns:
            Respuesta completa como string
        """
        try:
            if self.chatSession:
                print("Generando respuesta con sesión...")
                response = self.chatSession.send_message(
                    content=prompt,
                    stream=False
                )
                print("Respuesta completa recibida")
                return response.text
            else:
                print("Generando respuesta sin sesión...")
                response = self.model.generate_content(
                    contents=prompt,
                    stream=False
                )
                print("Respuesta completa recibida")
                return response.text
        except Exception as e:
            print(f"Error en chat(): {e}")
            return f"Error al generar respuesta: {str(e)}"

    def memory(self, prompt: str | List[Content]):
        response = self.model.generate_content(contents=prompt, stream=False)
        return response.text

    def _get_generic_fallback_response(self) -> str:
        """
        Respuesta genérica cuando otros métodos fallan
        """
        # response = self.fallback_responses[self.fallback_index % len(self.fallback_responses)]
        # self.fallback_index += 1
        # print(f"[DEBUG] Usando respuesta de fallback: {response}")
        # return response

    def reset_session(self):
        """
        Reinicia la sesión de chat en caso de problemas persistentes
        """
        if not self.chatSession:
            print("[DEBUG] No hay sesión activa para reiniciar")
            return
        try:
            print("[DEBUG] Reiniciando sesión de chat de VertexAI")
            self.chatSession = self.model.start_chat(response_validation=False)
            print("[DEBUG] Sesión reiniciada correctamente")
        except Exception as e:
            print(f"[ERROR] Error al reiniciar sesión: {e}")

    def get_session_history_length(self) -> int:
        if not self.chatSession:
            print("[DEBUG] No hay sesión activa para obtener historial")
            return 0
        """
        Obtiene la longitud del historial de la sesión actual
        """
        try:
            return len(self.chatSession.history)
        except:
            return 0