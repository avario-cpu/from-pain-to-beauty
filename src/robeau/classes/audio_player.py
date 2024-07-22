import json
import os
import random
import threading
import pygame


class AudioPlayer:
    pygame.mixer.init()  # Initialize pygame mixer globally

    def __init__(self, mappings_file):
        with open(mappings_file, "r") as file:
            self.audio_mappings = json.load(file)
        self.playing_thread = None
        self.stop_event = threading.Event()

    def play_audio(self, output_string: str, on_start=None, on_stop=None, on_end=None):
        if self.playing_thread and self.playing_thread.is_alive():
            self.stop_audio()

        self.stop_event.clear()
        self.playing_thread = threading.Thread(
            target=self._play_audio, args=(output_string, on_start, on_stop, on_end)
        )
        self.playing_thread.start()

    def _play_audio(self, output_string: str, on_start, on_stop, on_end):
        audio_files = self.audio_mappings.get(output_string)
        if not audio_files:
            print(f'No audio files found for "{output_string}".')
            if on_end:
                print("Calling on end from _play_audio")
                on_end()  # Notify that audio finished without playing
            return

        audio_file = self._select_weighted_random_file(audio_files)
        if not audio_file or not os.path.exists(audio_file):
            print(f'Audio file "{audio_file}" not found.')
            if on_end:
                print("Calling on end from _play_audio")
                on_end()  # Notify that audio finished without playing
            return

        if on_start:
            on_start()  # Notify that audio is starting

        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            if self.stop_event.is_set():
                pygame.mixer.music.stop()
                if on_stop:
                    on_stop()  # Notify that audio was stopped
                return
            pygame.time.wait(100)

        if not self.stop_event.is_set() and on_end:
            on_end()  # Notify that audio finished playing naturally

    def stop_audio(self):
        if self.playing_thread and self.playing_thread.is_alive():
            self.stop_event.set()
            self.playing_thread.join()

    def _select_weighted_random_file(self, audio_files):
        total_weight = sum(file["weight"] for file in audio_files)
        random_choice = random.uniform(0, total_weight)
        current_weight = 0

        for file in audio_files:
            current_weight += file["weight"]
            if current_weight >= random_choice:
                return file["file"]
