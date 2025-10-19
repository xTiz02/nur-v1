from enum import Enum

from src.com.model.enums import MultiModalEventType

MULTIMODAL_STRATEGY: MultiModalEventType = MultiModalEventType.NORMAL
PATIENCE = 2.0  # segundos de espera tras último fragmento para considerar finalizado el mensaje por discord
