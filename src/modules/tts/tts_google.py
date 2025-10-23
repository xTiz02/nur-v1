import itertools
import logging
import subprocess

from google.cloud import texttospeech

logger = logging.getLogger(__name__)

class GoogleTTSEngine:
    """
    Streaming TTS con Google Cloud Text-to-Speech (bidireccional).
    """
    def __init__(
        self,
        language: str = "es-US",
        voice_name: str = "es-US-Journey-F",
        sample_rate_hz: int = 48000,
        speaking_rate: float = 1.2,
    ):
        self.client = texttospeech.TextToSpeechClient()
        self.default_language = language
        self.default_voice_name = voice_name
        self.sample_rate_hz = sample_rate_hz
        self.speaking_rate = speaking_rate
        self.audio_config = texttospeech.StreamingAudioConfig(
            audio_encoding=texttospeech.AudioEncoding.OGG_OPUS,
        )

        self.streaming_config = texttospeech.StreamingSynthesizeConfig(
            voice=texttospeech.VoiceSelectionParams(
                name=voice_name,
                language_code=language,
            ),
            streaming_audio_config=self.audio_config
        )
    def synthesize_streaming(self, text: str):
        """
        Sintetiza texto completo y retorna chunks de audio.

        Args:
            text: Texto completo a sintetizar

        Yields:
            Bytes de audio PCM (chunks)
        """
        if not text or not text.strip():
            logger.warning("Texto vacío recibido")
            return

        try:
            logger.info(f"Sintetizando texto: {len(text)} caracteres")

            # Requests
            config_request = texttospeech.StreamingSynthesizeRequest(
                streaming_config=self.streaming_config
            )

            text_request = texttospeech.StreamingSynthesizeRequest(
                input=texttospeech.StreamingSynthesisInput(text=text)
            )

            # Llamar a Google TTS (blocking, pero retorna generator)
            logger.debug("Llamando a Google TTS API...")
            responses = self.client.streaming_synthesize(
                itertools.chain([config_request, text_request])
            )

            # Producir chunks de audio
            chunk_count = 0
            for response in responses:
                if response.audio_content:
                    chunk_count += 1
                    logger.debug(f"Chunk #{chunk_count}: {len(response.audio_content)} bytes")
                    yield response.audio_content

            logger.info(f"Síntesis completa: {chunk_count} chunks generados")

        except Exception as e:
            logger.error(f"Error en síntesis: {e}", exc_info=True)

    def process_audio_chunk(self, audio_chunk: bytes) -> bytes:
        """
        Procesa un chunk de audio recibido del stream.
        Aquí puedes agregar procesamiento adicional si es necesario.
        """
        return self._ogg_to_pcm48(audio_chunk)

    import subprocess

    def _ogg_to_pcm48(self, audio_bytes: bytes) -> bytes:
        """
        Convierte audio OGG_OPUS → PCM 16-bit mono 48kHz (raw)
        usando ffmpeg en memoria.
        """
        process = subprocess.Popen(
            ["ffmpeg", "-i", "pipe:0", "-f", "s16le", "-acodec", "pcm_s16le",
             "-ac", "1", "-ar", "48000", "pipe:1"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        pcm_data, _ = process.communicate(audio_bytes)
        return pcm_data
