import argparse
import asyncio
import os
import queue
import socket
from typing import Optional

import pyaudio
from google.cloud import speech

from src.config import settings
from src.config.setup import setup_script
from src.core import constants as const
from src.core.constants import SLOTS_DB_FILE_PATH
from src.utils import helpers

RATE = 16000
CHUNK = int(RATE / 10)  # 100ms
SCRIPT_NAME = helpers.construct_script_name(__file__)

DEFAULT_SERVER_HOST = "localhost"
ROBEAU_SERVER_PORT = const.SUBPROCESSES_PORTS["robeau"]
SYNONYMS_SERVER_PORT = const.SUBPROCESSES_PORTS["synonym_adder"]

if settings.GOOGLE_CLOUD_API_KEY is None:
    raise ValueError("Missing Google API Key")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_CLOUD_API_KEY

logger = helpers.setup_logger(SCRIPT_NAME)


class MicrophoneStream:
    """Opens a recording stream as a generator yielding the voice lines
    chunks."""

    def __init__(self, rate: int, chunk: int):
        self._rate = rate
        self._chunk = chunk
        self._buff: queue.Queue = queue.Queue()
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
            sock.sendall(transcript.encode("utf-8"))


async def recognize_speech(interim: bool, sock: Optional[socket.socket] = None):
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
        interim_results=interim,
    )

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        # noinspection PyTypeChecker
        requests = (
            speech.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )
        # noinspection PyArgumentList
        responses = client.streaming_recognize(streaming_config, requests)  # type: ignore
        await listen_print_loop(responses, sock)


# noinspection PyTypeChecker
async def main(interim: bool = False, socket_name: str = "robeau"):
    try:
        db_conn, slot = await setup_script(SCRIPT_NAME, SLOTS_DB_FILE_PATH)

        try:
            print("Attempting to connect to the specified socket...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if socket_name == "syn":
                sock.connect((DEFAULT_SERVER_HOST, SYNONYMS_SERVER_PORT))
            else:
                sock.connect((DEFAULT_SERVER_HOST, ROBEAU_SERVER_PORT))
            logger.info(f"Connected with {sock}")
            print(f"Connected with {sock}")
        except ConnectionError:
            print(f"Couldn't connect to the specified socket, proceeding without it.")
            sock = None

        await recognize_speech(interim, sock)

    except Exception as e:
        print(f"Unexpected error of type: {type(e).__name__}: {e}")
        logger.exception(f"Unexpected error: {e}")
        raise
    finally:
        if db_conn:
            await db_conn.close()


def str2bool(value):
    """Necessary for argparse to return an actual boolean value"""
    if value.lower() in ("true", "t"):
        return True
    elif value.lower() in ("false", "f"):
        return False
    else:
        raise argparse.ArgumentTypeError("Bool expected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="STT recognition stream")
    parser.add_argument("interim", type=str2bool, help="Interim value for stt stream")
    parser.add_argument(
        "--socket",
        type=str,
        choices=["robeau", "syn"],
        default="robeau",
        help="Specify which socket to connect to",
    )
    args = parser.parse_args()
    asyncio.run(main(args.interim, args.socket))
