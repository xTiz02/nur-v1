import asyncio
import discord
import numpy as np
from concurrent.futures import CancelledError

class StreamingAudio(discord.AudioSource):
    """
    AudioSource para Discord que recibe PCM 16-bit mono 48kHz desde un generador async,
    aplica ganancia, convierte a stereo y evita cortes gracias a un prebuffer.
    """
    BLOCK_SIZE = 960 * 2 * 2  # 960 samples, 2 bytes/sample, 2 canales (20ms aprox)

    def __init__(self, async_generator, loop=None, gain: float = 2.0):
        self.generator = async_generator.__aiter__()
        self.loop = loop or asyncio.get_event_loop()
        self.buffer = b""
        self.gain = gain
        self.lock = asyncio.Lock()
        self._prefill_done = False
        self._prefill_event = asyncio.Event()

        # Iniciar precarga del buffer en paralelo
        asyncio.run_coroutine_threadsafe(self._prefill_buffer(), self.loop)

    async def _prefill_buffer(self):
        """
        Carga algunos chunks (≈300ms de audio) antes de iniciar playback
        para evitar cortes iniciales.
        """
        try:
            collected = 0
            while collected < self.BLOCK_SIZE * 15:  # ~300ms de audio pre-cargado
                try:
                    chunk = await self._get_next_chunk()
                    if not chunk:
                        await asyncio.sleep(0.02)
                        continue

                    # 🔊 Procesamiento normal
                    audio = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
                    audio *= self.gain
                    audio = np.clip(audio, -32768, 32767)
                    stereo = np.column_stack((audio, audio)).ravel().astype(np.int16)
                    stereo_bytes = stereo.tobytes()

                    self.buffer += stereo_bytes
                    collected += len(stereo_bytes)
                except StopAsyncIteration:
                    break

            self._prefill_done = True
            self._prefill_event.set()
            print("[StreamingAudio] Prebuffer listo")
        except Exception as e:
            print("[StreamingAudio] Error en prebuffer:", e)

    async def _get_next_chunk(self):
        """Obtiene el siguiente chunk del generador de forma segura."""
        async with self.lock:
            return await self.generator.__anext__()

    def read(self):
        """Lee datos PCM ya preparados y suaviza la reproducción."""
        try:
            # Esperar prebuffer inicial
            if not self._prefill_done and not self._prefill_event.is_set():
                return b"\x00" * self.BLOCK_SIZE

            # Si ya hay datos en buffer, entregamos bloque
            if len(self.buffer) >= self.BLOCK_SIZE:
                chunk, self.buffer = self.buffer[:self.BLOCK_SIZE], self.buffer[self.BLOCK_SIZE:]
                return chunk

            # Intentar obtener más datos del async generator
            fut = asyncio.run_coroutine_threadsafe(self._get_next_chunk(), self.loop)
            try:
                chunk_mono = fut.result(timeout=2.0)
            except TimeoutError:
                # Si el TTS se demora, devolvemos un pequeño silencio
                asyncio.sleep(0.01)
                return b"\x00" * self.BLOCK_SIZE
            except StopAsyncIteration:
                return b""

            if not chunk_mono:
                return b"\x00" * self.BLOCK_SIZE

            # Procesamiento original
            audio = np.frombuffer(chunk_mono, dtype=np.int16).astype(np.float32)
            audio *= self.gain
            audio = np.clip(audio, -32768, 32767)
            stereo = np.column_stack((audio, audio)).ravel().astype(np.int16)
            self.buffer += stereo.tobytes()

            # Retornar bloque
            if len(self.buffer) >= self.BLOCK_SIZE:
                chunk, self.buffer = self.buffer[:self.BLOCK_SIZE], self.buffer[self.BLOCK_SIZE:]
                return chunk
            else:
                # Si no hay suficiente, rellena con silencio (suaviza cortes)
                diff = self.BLOCK_SIZE - len(self.buffer)
                chunk, self.buffer = self.buffer + (b"\x00" * diff), b""
                return chunk

        except CancelledError:
            return b"\x00" * self.BLOCK_SIZE
        except Exception as e:
            print("[StreamingAudio] Error:", e)
            return b"\x00" * self.BLOCK_SIZE

    def is_opus(self):
        return False
