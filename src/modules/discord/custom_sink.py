import time

from discord.ext import voice_recv
import discord
from src.modules.discord.fragment import FragmentManager

class LoggingSpeechRecognitionSink(voice_recv.extras.speechrecognition.SpeechRecognitionSink):

    def __init__(self, *args, signals=None, manager:FragmentManager, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = signals
        self.manager = manager

    @voice_recv.AudioSink.listener()
    def on_voice_member_speaking_start(self, member: discord.Member):
        print(f"{member.display_name} empezó a hablar")
        if self.signals:
            self.signals.human_speaking = True

    @voice_recv.AudioSink.listener()
    def on_voice_member_speaking_stop(self, member: discord.Member):
        print(f"{member.display_name} dejó de hablar")
        if self.signals:
            self.signals.human_speaking = False

    @voice_recv.AudioSink.listener()
    def on_voice_member_disconnect(self, member: discord.Member, ssrc: int | None):
        print(f"{member.display_name} se desconectó del canal (ssrc={ssrc})")