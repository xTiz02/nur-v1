import asyncio
import io
import numpy as np
import discord
from discord.ext import commands, voice_recv

from src.com.model.enums import EventType
from src.module import Module
import env
import speech_recognition as sr

from src.modules.discord.custom_sink import LoggingSpeechRecognitionSink
from src.modules.discord.fragment import FragmentManager
from src.modules.stt.stt_interface import STTInterface

# Clase simple para simular un objeto usuario
class SimpleUser:
    def __init__(self, user_id, display_name):
        self.id = user_id
        self.display_name = display_name

def make_recognizer():
    print("[DEBUG] Creando recognizer de SpeechRecognition")
    r = sr.Recognizer()
    r.energy_threshold = 200 # Nivel mínimo de volumen para detectar voz (ajusta según pruebas)
    r.dynamic_energy_threshold = True # Se adapta al ruido de fondo
    r.pause_threshold = 4.0 # Tiempo de silencio antes de cortar frase
    r.phrase_threshold = 1.2 # Tiempo mínimo de voz para considerarlo frase
    r.non_speaking_duration = 0.8 # Silencios muy cortos los ignora
    return r

class DiscordClient(Module):
    def __init__(self, signals, stt: STTInterface, manager: FragmentManager, enabled=True):
        super().__init__(signals, enabled)
        self.stt = stt
        self.manager = manager
        self.vc = None  # conexión de voz
        self.play_task = None  # tarea async para reproducir
        self.general_channel = None  # canal de texto para enviar mensajes

    def _process_audio(self, recognizer: sr.Recognizer, audio: sr.AudioData, user):
        self.signals.process_text = True
        print(f"[DEBUG] _process_audio() llamado para usuario {user.display_name}")
        try:
            text = self.stt.transcribe(recognizer, audio, user.display_name)
            if text:
                print(f"[DEBUG] Fragmento reconocido: {text}")
                self.manager.process_fragment(user, text)
        except Exception as e:
            print(f"[ERROR] Fallo en _process_audio: {e}")
        self.signals.process_text = False
        return None


    async def _play_from_queue(self):
        """Lee audio completo (PCM 16-bit mono 48kHz) desde la cola y lo reproduce."""
        print("[DEBUG] _play_from_queue() iniciado")
        while not self.signals.terminate :
            if self.signals.tts_ready:
                try:
                    # Esperar audio desde la cola (bloque único)
                    audio_bytes = await asyncio.get_event_loop().run_in_executor(None, self.signals.audio_queue.get)
                    if not audio_bytes or not self.vc or not self.vc.is_connected():
                        self.signals.AI_speaking = False
                        await asyncio.sleep(0.05)
                        continue
                    # Convertir mono → estéreo
                    self.signals.AI_speaking = True
                    audio = np.frombuffer(audio_bytes, dtype=np.int16)
                    stereo = np.repeat(audio[:, None], 2, axis=1).ravel().astype(np.int16)
                    stereo_bytes = stereo.tobytes()
                    # Crear un objeto PCMAudio para Discord
                    source = discord.PCMAudio(io.BytesIO(stereo_bytes))
                    print("[DEBUG] Reproduciendo audio completo (PCM LINEAR16 -> estéreo 48kHz)")
                    self.vc.play(source)
                    # Esperar a que termine
                    while self.vc.is_playing():
                        await asyncio.sleep(0.05)

                    self.signals.AI_speaking = False
                except Exception as e:
                    print(f"[ERROR] en _play_from_queue: {e}")
                    await asyncio.sleep(0.1)
                    self.signals.AI_speaking = False
            else:
                # obtener el siguiente item de la queue sin bloquear el event loop
                item = await asyncio.get_event_loop().run_in_executor(None, self.signals.sio_queue.get)
                if item is None:
                    continue
                # la queue almacena (EventType, payload) o similar
                event, payload = item
                # aceptar tanto el enum como el string "next_chunk"
                if event == EventType.NEXT_CHUNK:
                    text = payload
                else:
                    # ignorar otros eventos y seguir leyendo
                    continue
                print(f"[DEBUG] Enviando mensaje al canal de texto: ")
                await self.general_channel.send(text)


    async def run(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        commands_bot = commands.Bot(command_prefix='$', intents=intents)
        bot = commands_bot
        connections = {}

        if not self.play_task or self.play_task.done():
            print(f"[DEBUG] Iniciar tarea de reproducción de audio desde la cola.")
            loop = asyncio.get_event_loop()
            self.play_task = loop.create_task(self._play_from_queue())

        @bot.event
        async def on_ready():
            self.general_channel = bot.get_channel(env.GENERAL_CHANNEL_ID)
            if self.general_channel:
                print("[DEBUG] Canal de texto general obtenido correctamente.")

            await self.general_channel.send("¡Hola! Estoy en línea y listo para transcribir y responder.")

        @bot.command(name="ping", description="Check the bot's status")
        async def ping(ctx):
            await ctx.send(f"Pong! {bot.latency}")

        # async def finished_callback(sink, channel: discord.TextChannel, *args):
        #     await sink.vc.disconnect()
        #     await channel.send("Finished!")
        @bot.command(name="chat", description="Send message to AI")
        async def chat(ctx, *args ):
            """Send a message to the AI."""
            print(f"[DEBUG] chat() llamado con args: {' '.join(args)}")
            if len(' '.join(args)) > 6:
                self.signals.process_text = True
                text = ' '.join(args)
                user = SimpleUser(
                    user_id=ctx.author.id,
                    display_name=ctx.author.name
                )
                print(f"[DEBUG] Procesando fragmento desde chat(): {text}")
                self.manager.process_fragment(user, text)
                self.signals.process_text = False

        @bot.command(name="start", description="Bot will join your vc")
        async def start(ctx):
            """Record your voice!"""
            if ctx.author.voice:
                print("[DEBUG] Usuario en canal de voz, intentando conectar...")
                vc: voice_recv.VoiceRecvClient = await ctx.author.voice.channel.connect(
                    cls=voice_recv.VoiceRecvClient
                )
                self.vc = vc

                print("[DEBUG] Conectado al canal de voz")
                sink = LoggingSpeechRecognitionSink(
                    process_cb=lambda recognizer, audio, user: self._process_audio(recognizer, audio, user),
                    text_cb=lambda u, t: None,  # desactivamos text_cb directo
                    default_recognizer="google",
                    phrase_time_limit=60,
                    recognizer_factory=make_recognizer,
                    signals=self.signals,
                    manager=self.manager
                )
                self.signals.tts_ready = True
                print("[DEBUG] Iniciando escucha con SpeechRecognitionSink...")
                vc.listen(sink)
                await ctx.send("Estoy escuchando y transcribiendo con Google.")
            else:
                print("[DEBUG] join() falló: usuario no está en canal de voz")
                await ctx.send("No estás en un canal de voz.")

        @bot.command(name="stop", description="Bot will exit the vc")
        async def stop(ctx):
            """Stop recording."""
            if ctx.guild.id in connections and ctx.voice_client:
                del connections[ctx.guild.id]
                await ctx.voice_client.disconnect()
            else:
                await ctx.send("Not recording in this guild.")

        await bot.start(env.TOKEN)
        # bot.run(env.TOKEN)