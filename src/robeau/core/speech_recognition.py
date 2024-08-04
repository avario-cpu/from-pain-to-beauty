import os
import queue
import threading
from typing import Optional

import pyaudio
from google.cloud import speech

from src.config.settings import GOOGLE_CLOUD_API_KEY

RATE = 16000
CHUNK = int(RATE / 10)  # 100ms


if GOOGLE_CLOUD_API_KEY is None:
    raise ValueError("Missing Google API Key")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CLOUD_API_KEY


class MicrophoneStream:
    """Opens a recording stream as a generator yielding the voice lines chunks."""

    def __init__(
        self, rate: int, chunk: int, pause_event: Optional[threading.Event] = None
    ):
        self._rate = rate
        self._chunk = chunk
        self._buff: queue.Queue = queue.Queue()
        self.closed = True
        self.pause_event = pause_event
        self._audio_interface = None
        self._audio_stream = None

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


async def listen_print_loop(
    responses, handler, pause_event: Optional[threading.Event] = None
):
    for response in responses:
        if not response.results:
            continue
        result = response.results[0]
        if not result.alternatives:
            continue
        transcript = result.alternatives[0].transcript
        if result.is_final:
            await handler.handle_message(transcript)
            if pause_event is not None:
                pause_event.clear()
                print("cleared pause event")
        else:
            print(f"Interim: {transcript}")
            if pause_event is not None:
                pause_event.set()


# noinspection PyTypeChecker, PyArgumentList
# Really no idea why there are so many type errors here, but it works totally fine
async def recognize_speech(handler, pause_event: Optional[threading.Event] = None):
    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="en-US",
    )
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,
    )

    with MicrophoneStream(RATE, CHUNK, pause_event=pause_event) as stream:

        audio_generator = stream.generator()
        requests = (
            speech.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )

        # pylint: disable=E1123
        responses = client.streaming_recognize(
            config=streaming_config,
            requests=requests,
        )  # type: ignore
        await listen_print_loop(responses, handler, pause_event)
