import os
import discord
from discord.ext import commands, voice_recv
from modules.module import Module
import env
import speech_recognition as sr

from modules.service.stt.stt_interface import STTInterface


def make_recognizer():
    print("[DEBUG] Creando recognizer de SpeechRecognition")
    r = sr.Recognizer()
    r.energy_threshold = 200
    r.dynamic_energy_threshold = True
    r.pause_threshold = 4.0
    r.phrase_threshold = 1.2
    r.non_speaking_duration = 0.8
    return r

class DiscordClient(Module):
    def __init__(self, signals, stt: STTInterface, enabled=True):
        super().__init__(signals, enabled)

        self.stt = stt

    def _process_audio(self, recognizer: sr.Recognizer, audio: sr.AudioData, user):
        print(f"[DEBUG] _process_audio() llamado para usuario {user.display_name}, is_speaking={self._is_speaking}")

        try:
            text = self.stt.transcribe(recognizer, audio, user.display_name)
            if text:
                print(f"[DEBUG] Fragmento reconocido: {text}")

                # Si la IA está hablando, guardar en buffer pendiente
                # if self._is_speaking:
                #     print(f"[DEBUG] IA hablando, guardando en buffer pendiente: {text}")
                #     user_id = user.id
                #     if user_id not in self._pending_audio:
                #         self._pending_audio[user_id] = {
                #             'user': user,
                #             'fragments': []
                #         }
                #     self._pending_audio[user_id]['fragments'].append(text)
                # else:
                #     # Procesamiento normal
                #     self._add_fragment(user, text)

            return None
        except Exception as e:
            print(f"[ERROR] Fallo en _process_audio: {e}")
            return None

    async def run(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        commands_bot = commands.Bot(command_prefix='$', intents=intents)
        bot = commands_bot
        connections = {}

        @bot.event
        async def on_ready():
            print(f"{bot.user} is online.")

        @bot.command(name="ping", description="Check the bot's status")
        async def ping(ctx):
            await ctx.respond(f"Pong! {bot.latency}")

        async def finished_callback(sink, channel: discord.TextChannel, *args):
            await sink.vc.disconnect()
            await channel.send("Finished!")

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

                sink = voice_recv.extras.speechrecognition.SpeechRecognitionSink(
                    process_cb=lambda recognizer, audio, user: self._process_audio(recognizer, audio, user),
                    default_recognizer="google",
                    phrase_time_limit=60,
                    recognizer_factory=make_recognizer
                )

                print("[DEBUG] Iniciando escucha con SpeechRecognitionSink...")
                vc.listen(sink)
                await ctx.send("Estoy escuchando y transcribiendo con Google.")
            else:
                print("[DEBUG] join() falló: usuario no está en canal de voz")
                await ctx.send("No estás en un canal de voz.")

        @bot.command(name="stop", description="Bot will exit the vc")
        async def stop(ctx: discord.ApplicationContext):
            """Stop recording."""
            if ctx.guild.id in connections:
                vc = connections[ctx.guild.id]
                vc.stop_recording()
                del connections[ctx.guild.id]
                await ctx.delete()
            else:
                await ctx.respond("Not recording in this guild.")

        bot.run(env.TOKEN)