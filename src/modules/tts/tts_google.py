import itertools
from pathlib import Path

import numpy as np
from google.cloud import texttospeech

class GoogleTTSEngine:
    """
    Streaming TTS con Google Cloud Text-to-Speech (bidireccional).
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
        self.audio_config = texttospeech.StreamingAudioConfig(
            audio_encoding=texttospeech.AudioEncoding.PCM,
            sample_rate_hertz=48000,
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
            print("Texto vacío recibido")
            return

        try:
            print(f"Sintetizando texto: {len(text)} caracteres")

            # Requests
            config_request = texttospeech.StreamingSynthesizeRequest(
                streaming_config=self.streaming_config
            )

            text_request = texttospeech.StreamingSynthesizeRequest(
                input=texttospeech.StreamingSynthesisInput(text=text)
            )

            # Llamar a Google TTS (blocking, pero retorna generator)
            print("Llamando a Google TTS API...")
            responses = self.client.streaming_synthesize(
                itertools.chain([config_request, text_request])
            )

            # Producir chunks de audio
            chunk_count = 0
            for response in responses:
                if response.audio_content:
                    chunk_count += 1
                    print(f"Chunk #{chunk_count}: {len(response.audio_content)} bytes")
                    yield response.audio_content

            print(f"Síntesis completa: {chunk_count} chunks generados")

        except Exception as e:
            print(f"Error en síntesis: {e}", exc_info=True)

    def synthesize_full(self, text: str, *, language: str = None, voice: str = None, save_path: str = None) -> bytes:
        """
        Sintetiza texto completo y retorna todo el audio en un solo bloque PCM 16-bit.
        Si 'save_path' está definido, guarda el audio como WAV.

        Returns:
            Bytes de audio PCM
        """
        language = language or self.default_language
        voice = voice or self.default_voice_name

        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice_params = texttospeech.VoiceSelectionParams(
                language_code=language, name=voice
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.sample_rate_hz,
                speaking_rate=self.speaking_rate,
            )

            print(f"[TTS] Sintetizando (modo completo): {len(text)} caracteres")
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice_params, audio_config=audio_config
            )

            audio_bytes = response.audio_content
            print(f"[TTS] Recibido audio: {len(audio_bytes)} bytes")

            # Guardar archivo si se indicó una ruta
            if save_path:
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(audio_bytes)
                print(f"[TTS] Audio guardado en: {save_path}")

            return audio_bytes

        except Exception as e:
            print(f"[TTS] Error en síntesis completa: {e}", exc_info=True)
            return b""