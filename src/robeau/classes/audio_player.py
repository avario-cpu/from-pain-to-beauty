import json
import os
import random
import threading
import pygame
from logging import Logger
from threading import Event, Thread
from typing import Literal, Optional


class AudioPlayer:
    pygame.mixer.init()

    def __init__(self, mappings_file, logger: Logger):
        with open(mappings_file, "r") as file:
            self.audio_mappings = json.load(file)
        self.logger = logger
        self.playing_threads: list[Thread] = []
        self.stop_events: list[Event] = []
        self.threads_to_join: list[Thread] = []
        self.lock = threading.Lock()
        self.active_threads = 0

        # Callbacks
        self.on_start = None
        self.on_stop = None
        self.on_end = None
        self.on_error = None

        # To manage groups of threads
        self.group_count = 1
        self.current_group_start_count = 0
        self.current_group_done_count = 0

    def set_callbacks(self, on_start=None, on_stop=None, on_end=None, on_error=None):
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_end = on_end
        self.on_error = on_error

    def play_audio(self, output_string: str, multiple_tracks: Optional[int] = False):
        self.group_count = multiple_tracks if multiple_tracks else 1
        stop_event = threading.Event()
        thread_name = f"AudioThread-{output_string}-{len(self.playing_threads) + 1}"
        thread = threading.Thread(
            target=self._play_audio,
            args=(output_string, stop_event),
            name=thread_name,
            daemon=True,
        )
        with self.lock:
            self.playing_threads.append(thread)
            self.stop_events.append(stop_event)
            self.active_threads += 1
        thread.start()
        self.logger.info(f"Started thread {thread_name}")

    def _play_audio(self, output_string: str, stop_event):
        try:
            audio_files = self.audio_mappings.get(output_string)
            if not audio_files:
                self.logger.warning(f"No audio files found for <<{output_string}>>.")
                self._thread_done(stop_event, termination_reason="error")
                return

            audio_file = self._select_weighted_random_file(audio_files)
            if not audio_file or not os.path.exists(audio_file):
                self.logger.warning(f'Audio file "{audio_file}" not found.')
                self._thread_done(stop_event, termination_reason="error")
                return

            self.logger.info(f"Starting to play audio for: <<{output_string}>>")

            with self.lock:
                self.current_group_start_count += 1
                if self.current_group_start_count == self.group_count:
                    self.logger.info(f"Calling on_start() callback.")
                    if self.on_start:
                        self.on_start()
                    self.current_group_start_count = 0

            sound = pygame.mixer.Sound(audio_file)
            channel = sound.play()

            self.logger.info(f"Playing audio file: {audio_file}")
            while channel.get_busy():
                if stop_event.is_set():
                    channel.stop()
                    self._thread_done(stop_event, termination_reason="stop")
                    return
                pygame.time.wait(5)  # Reduce the wait time to check more frequently

            self.logger.info(
                f"Thread for <<{output_string}>> finished playing naturally."
            )
            self._thread_done(stop_event, termination_reason="end")

        except Exception as e:
            self.logger.exception(f"Exception in _play_audio: {str(e)}")
            self._thread_done(stop_event, termination_reason="error")

    def stop_audio(self):
        self.logger.info("Stopping all audio.")
        with self.lock:
            for stop_event in self.stop_events:
                stop_event.set()  # Signal all threads to stop

    def _select_weighted_random_file(self, audio_files):
        total_weight = sum(file["weight"] for file in audio_files)
        random_choice = random.uniform(0, total_weight)
        current_weight = 0

        for file in audio_files:
            current_weight += file["weight"]
            if current_weight >= random_choice:
                return file["file"]

    def _thread_done(
        self, stop_event, termination_reason: Literal["stop", "end", "error"]
    ):
        with self.lock:
            try:
                index = self.stop_events.index(stop_event)
                thread = self.playing_threads.pop(index)
                self.stop_events.pop(index)
                self.threads_to_join.append(thread)  # Add thread to list to join later
            except ValueError:
                self.logger.error("Error removing thread or stop event.")
                return

            self.active_threads -= 1
            self.current_group_done_count += 1

            self.logger.info(
                f"Thread done by: {termination_reason}. Active threads remaining: {self.active_threads}"
            )

            if self.current_group_done_count == self.group_count:
                self.current_group_done_count = 0
                if termination_reason == "stop":
                    self.logger.info(f"Calling on_stop() callback.")
                    if self.on_stop:
                        self.on_stop()
                elif termination_reason == "end":
                    self.logger.info(f"Calling on_end() callback.")
                    if self.on_end:
                        self.on_end()
                elif termination_reason == "error":
                    self.logger.info(f"Calling on_error() callback.")
                    if self.on_error:
                        self.on_error()

                self.playing_threads.clear()
                self.stop_events.clear()

    def join_threads(self):
        """Join threads that have finished their work."""
        self.logger.info("Joining completed threads.")
        for thread in self.threads_to_join:
            thread.join()
        self.threads_to_join.clear()
