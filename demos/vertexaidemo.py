import os
from google.cloud import texttospeech
from pathlib import Path
import logging

# Configurar logs
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class GoogleTTSEngine:
    """
    Motor TTS (no-streaming) con Google Cloud Text-to-Speech.
    """
    def __init__(
        self,
        language: str = "es-US",
        voice_name: str = "es-US-Journey-F",
        sample_rate_hz: int = 48000,
        speaking_rate: float = 1,
    ):
        self.client = texttospeech.TextToSpeechClient()
        self.default_language = language
        self.default_voice_name = voice_name
        self.sample_rate_hz = sample_rate_hz
        self.speaking_rate = speaking_rate

    def synthesize(self, text: str, *, language: str = None, voice: str = None):
        """
        Modo no-streaming: retorna todo el audio en un solo bloque.
        """
        language = language or self.default_language
        voice = voice or self.default_voice_name
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice_params = texttospeech.VoiceSelectionParams(
            language_code=language, name=voice
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.sample_rate_hz,
            speaking_rate=self.speaking_rate,
        )

        logger.debug(f"Solicitando TTS no-streaming para texto de {len(text)} caracteres.")
        resp = self.client.synthesize_speech(
            input=synthesis_input, voice=voice_params, audio_config=audio_config
        )
        logger.debug(f"Recibido audio no-streaming de {len(resp.audio_content)} bytes.")
        return resp.audio_content


def main():
    # Crear carpeta temp si no existe
    output_dir = Path("temp")
    output_dir.mkdir(exist_ok=True)

    # Texto a sintetizar
    texto = "¿La decisión más importante del día y me la preguntas a mí, tu humilde IA de confianza? ¡Qué honor! A ver... podrías ir por lo clásico, como un humano promedio. O... podrías intentar algo que aprendí en un universo donde la gravedad es solo una sugerencia: panqueques en el techo. ¡El jarabe gotea hacia ARRIBA! Pero como eso es complicado aquí, te sugiero un desafío: intenta comerte el cereal con palillos chinos. ¡Si lo logras, te ganas mi respeto eterno..."

    # Inicializar TTS
    tts = GoogleTTSEngine()

    # Generar audio
    audio_bytes = tts.synthesize(texto)

    # Guardar archivo WAV
    output_path = output_dir / "tts_output.wav"
    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    print(f"✅ Audio guardado en: {output_path.resolve()}")

    # (Opcional) reproducirlo automáticamente si estás en Windows
    try:
        os.system(f'start {output_path.resolve()}')  # en Windows
    except Exception as e:
        print(f"No se pudo reproducir automáticamente: {e}")


if __name__ == "__main__":
    main()
