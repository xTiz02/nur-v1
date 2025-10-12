from discord.ext import voice_recv
import discord
from src.modules.discord.fragment import FragmentManager
from utils.constans import EventType
import time

class LoggingSpeechRecognitionSink(voice_recv.extras.speechrecognition.SpeechRecognitionSink):

    def __init__(self, *args, signals=None, manager:FragmentManager, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = signals
        self.manager = manager

    @voice_recv.AudioSink.listener()
    def on_voice_member_speaking_start(self, member: discord.Member):
        print(f"{member.display_name} empezó a hablar")
        if self.signals:
            self.signals.sio_queue.put((EventType.HUMAN_SPEAKING, True))

    @voice_recv.AudioSink.listener()
    def on_voice_member_speaking_stop(self, member: discord.Member):
        current_time = time.time()
        print(f"{member.display_name} dejó de hablar")
        if self.signals:
            self.signals.sio_queue.put((EventType.HUMAN_SPEAKING, False))
        fragments = self.manager.get_user_buffers
        if fragments:
            last_fragment_time = fragments[-1].timestamp
            if current_time - last_fragment_time >= 4.0:
                full_fragments = self.manager.get_full_fragments() # Obtiene los fragmentos completos

        # # Si ya había un timer corriendo, cancelarlo
        # if member in silence_timers and not silence_timers[member].done():
        #   silence_timers[member].cancel()
        #
        # # Nuevo timer para cerrar buffer después de silencio prolongado
        # async def silence_wait():
        #   try:
        #     await asyncio.sleep(1.5)  # tiempo de silencio para confirmar fin de frase
        #     full_text = flush_user_buffer(member)
        #     if full_text:
        #       got_text(member, full_text)
        #   except asyncio.CancelledError:
        #     pass
        #
        # silence_timers[member] = loop.create_task(silence_wait())

    @voice_recv.AudioSink.listener()
    def on_voice_member_disconnect(self, member: discord.Member, ssrc: int | None):
        print(f"{member.display_name} se desconectó del canal (ssrc={ssrc})")