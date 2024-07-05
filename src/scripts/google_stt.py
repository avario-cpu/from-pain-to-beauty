import asyncio
import atexit
import os
import queue
import socket

import aiosqlite
import pyaudio
from google.cloud import speech

from src.config import settings
from src.core import constants as const
from src.core import slots_db_handler as sdh
from src.core import terminal_window_manager_v4 as twm
from src.core import utils

RATE = 16000
CHUNK = int(RATE / 10)  # 100ms
SCRIPT_NAME = utils.construct_script_name(__file__)

SERVER_HOST = 'localhost'
SERVER_PORT = const.SUBPROCESSES_PORTS['robeau']

os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS

logger = utils.setup_logger(SCRIPT_NAME)


class MicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self, rate: int, chunk: int):
        self._rate = rate
        self._chunk = chunk
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()

    # _ in front of param means I don't use the param (Avoid Pycharm warning)
    def _fill_buffer(self, in_data, _frame_count, _time_info, _status_flags):
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break
            yield b"".join(data)


async def listen_print_loop(responses, sock=None):
    for response in responses:
        if not response.results:
            continue
        result = response.results[0]
        if not result.alternatives:
            continue
        transcript = result.alternatives[0].transcript
        print(transcript)
        if sock:
            sock.sendall(transcript.encode('utf-8'))


async def recognize_speech(sock: socket.socket = None):
    client = speech.SpeechClient()
    # noinspection PyTypeChecker
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="en-US",
    )
    # noinspection PyTypeChecker
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,
    )

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        # noinspection PyTypeChecker
        requests = (speech.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)
        # noinspection PyArgumentList
        responses = client.streaming_recognize(streaming_config, requests)
        await listen_print_loop(responses, sock)


async def refuse_script_instance(db_conn: aiosqlite.Connection):
    slot, name = await twm.manage_window(db_conn, twm.WinType.DENIED,
                                         SCRIPT_NAME)
    atexit.register(sdh.free_denied_slot_sync, slot)
    print("\n>>> Lock file is present: exiting... <<<")


async def initialize_main_task(db_conn: aiosqlite.Connection,
                               lock_file_manager: utils.LockFileManager) \
        -> socket.socket:
    await twm.manage_window(db_conn, twm.WinType.ACCEPTED, SCRIPT_NAME)

    lock_file_manager.create_lock_file(SCRIPT_NAME)
    atexit.register(lock_file_manager.remove_lock_file, SCRIPT_NAME)
    atexit.register(sdh.free_slot_by_name_sync,
                    twm.WINDOW_NAME_SUFFIX + SCRIPT_NAME)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_HOST, SERVER_PORT))
        return sock
    except ConnectionError as e:
        print(f"Couldn't connect: {e}")


async def run_main_task(sock: socket.socket):
    await recognize_speech(sock)


# noinspection PyTypeChecker
async def main():
    db_conn = None

    try:
        lock_file_manager = utils.LockFileManager()
        db_conn = await sdh.create_connection(const.SLOTS_DB_FILE_PATH)

        if lock_file_manager.lock_exists(SCRIPT_NAME):
            await refuse_script_instance(db_conn)
            return

        sock = await initialize_main_task(db_conn, lock_file_manager)

        await run_main_task(sock)

    except Exception as e:
        print(f"Unexpected error of type: {type(e).__name__}: {e}")
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        if db_conn:
            await db_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
