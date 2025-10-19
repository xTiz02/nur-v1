# Python Module Imports
import signal
import sys
import time
import threading
import asyncio

from src.modules.discord.bot import DiscordClient
from src.modules.discord.fragment import FragmentManager
from src.modules.stt.stt_google import GoogleSTTEngine
from src.prompter import Prompter
# Class Imports
from utils.signals import Signals
# from prompter import Prompter
# from llmWrappers.llmState import LLMState
# from llmWrappers.textLLMWrapper import TextLLMWrapper
# from llmWrappers.imageLLMWrapper import ImageLLMWrapper
# from stt import STT
# from tts import TTS
# from src.twitchClient import TwitchClient
# from src.audioPlayer import AudioPlayer
# from src.vtubeStudio import VtubeStudio
# from src.multimodal import MultiModal
# from src.customPrompt import CustomPrompt
# from src.memory import Memory
# from socketioServer import SocketIOServer


def run_discord_bot(signals, stt, fragment_manager):
    """Función que corre el bot en un hilo separado con su propio event loop"""
    async def runner():
        bot = DiscordClient(signals, stt, fragment_manager, enabled=False)
        await bot.run()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(runner())
    except Exception as e:
        print(f"[ERROR] Discord bot loop terminó con error: {e}")
    finally:
        loop.close()
        print("[INFO] Discord bot loop cerrado.")


async def main():
    print("Starting Project...")

    # Registra un manejador de señales para que todos los hilos puedan salir.
    def signal_handler(sig, frame):
        print('Si esto no funciona, presiona CTRL + C de nuevo para forzar el cierre de la aplicación.')
        signals.terminate = True
        # stt.API.shutdown()

    signal.signal(signal.SIGINT, signal_handler) # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler) # Terminar proceso desde el SO (o Docker)

    # CORE FILES

    # Singleton object that every module will be able to read/write to
    signals = Signals()

    # MODULES
    # Modules that start disabled CANNOT be enabled while the program is running.
    modules = {}
    module_threads = {}

    # Create STT
    # stt = STT(signals)
    # Create TTS
    # tts = TTS(signals)
    # Create LLMWrappers
    # llmState = LLMState()
    # llms = {
    #     "text": TextLLMWrapper(signals, tts, llmState, src),
    #     "image": ImageLLMWrapper(signals, tts, llmState, src)
    # }
    # Create Prompter
    fragment_manager = FragmentManager(signals)
    prompter = Prompter(signals, None,fragment_manager, None)

    # Create Discord bot
    stt = GoogleSTTEngine()
    # modules['discord'] = DiscordClient(signals, stt,fragment_manager, enabled=False)
    # Hilo del bot
    bot_thread = threading.Thread(
        target=run_discord_bot, args=(signals, stt, fragment_manager), daemon=True
    )
    bot_thread.start()
    # discord_bot = DiscordClient(signals, stt,fragment_manager, enabled=False)
    # await discord_bot.run()
    # Create Twitch bot
    # src['twitch'] = TwitchClient(signals, enabled=False)
    # Create audio player
    # src['audio_player'] = AudioPlayer(signals, enabled=True)
    # Create Vtube Studio plugin
    # src['vtube_studio'] = VtubeStudio(signals, enabled=True)
    # Create Multimodal module
    # src['multimodal'] = MultiModal(signals, enabled=False)
    # Create Custom Prompt module
    # src['custom_prompt'] = CustomPrompt(signals, enabled=True)
    # Create Memory module
    # src['memory'] = Memory(signals, enabled=True)

    # Create Socket.io server
    # The specific llmWrapper it gets doesn't matter since state is shared between all llmWrappers
    # sio = SocketIOServer(signals, stt, tts, llms["text"], prompter, src=src)

    # Create threads (As daemons, so they exit when the main thread exits)
    prompter_thread = threading.Thread(target=prompter.prompt_loop, daemon=True)
    # stt_thread = threading.Thread(target=stt.listen_loop, daemon=True)
    # sio_thread = threading.Thread(target=sio.start_server, daemon=True)
    # Start Threads
    # sio_thread.start()
    prompter_thread.start()
    # stt_thread.start()

    # Crear 1 hilo por cada módulo
    # for name, module in modules.items():
    #     module_thread = threading.Thread(target=module.init_event_loop, daemon=True)
    #     module_threads[name] = module_thread
    #     module_thread.start()

    while not signals.terminate:
        time.sleep(0.1)
    print("TERMINATING ======================")

    # Wait for child threads to exit before exiting main thread

    # Wait for all src to finish
    for module_thread in module_threads.values():
        module_thread.join()

    # sio_thread.join()
    # print("SIO EXITED ======================")
    prompter_thread.join()
    # print("PROMPTER EXITED ======================")
    # stt_thread.join()
    # print("STT EXITED ======================")

    print("All threads exited, shutdown complete")
    sys.exit(0)

if __name__ == '__main__':
    asyncio.run(main())