from enum import Enum

from enum import Enum

class EventType(Enum):
    # Eventos del humano
    HUMAN_SPEAKING: str = "human_speaking"

    # Eventos del AI
    AI_SPEAKING = "ai_speaking"
    AI_THINKING = "ai_thinking"

    # Eventos generales
    NEW_MESSAGE = "new_message"
    TTS_READY = "tts_ready"
    STT_READY = "stt_ready"
    RECENT_TWITCH_MESSAGES = "recent_twitch_messages"
    HISTORY_UPDATED = "history_updated"

    # Finalización o control del flujo
    TERMINATE = "terminate"
    TTS_FINISHED = "tts_finished"
    FRAGMENT_ADDED = "fragment_added"

