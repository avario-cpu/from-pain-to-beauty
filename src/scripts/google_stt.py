"""
Ugly ass module with nine billion warning that stress me out, but apparently
it's working just fine so, whatever, let's hide all that in some  function
I'll call from my subprocesses....
"""
import asyncio
import os
import sys

import pyaudio
import queue
from google.cloud import speech_v1p1beta1 as speech

print("Initial sys.path are :")
for p in sys.path:
    print(p)
#
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__),
#                                             '../..'))

project_root = "C:\\Users\\ville\\MyMegaScript"

print(f"project root: {project_root}")

# Add the project root to the sys.path
if project_root not in sys.path:
    sys.path.append(project_root)
    print("Added project root to sys.path\n")
    for p in sys.path:
        print(p)

from src.config import settings

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms


class MicrophoneStream:
    def __init__(self, rate, chunk):
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

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
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


async def listen_print_loop(responses, transcription_queue, mute_prints=False):
    for response in responses:
        if not response.results:
            continue
        result = response.results[0]
        if not result.alternatives:
            continue
        transcript = result.alternatives[0].transcript
        await transcription_queue.put(transcript)
        if not mute_prints:
            print("Transcript: {}".format(transcript))


def stream_speech_to_text(google_credentials: str,
                          transcriptions_queue: asyncio.Queue,
                          rate=RATE, chunk=CHUNK,
                          language_code="en-US", use_enhanced=True,
                          model="command_and_search",
                          mute_prints: bool = False):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_credentials

    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=rate,
        language_code=language_code,
        use_enhanced=use_enhanced,
        model=model,
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,
    )

    with MicrophoneStream(rate, chunk) as stream:
        audio_generator = stream.generator()
        requests = (speech.StreamingRecognizeRequest(audio_content=content) for
                    content in audio_generator)

        responses = client.streaming_recognize(streaming_config, requests)
        listen_print_loop(responses, mute_prints)


if __name__ == "__main__":
    creds = settings.GOOGLE_APPLICATION_CREDENTIALS
    transcriptions_queue = asyncio.Queue()
    stream_speech_to_text(creds, transcriptions_queue)
