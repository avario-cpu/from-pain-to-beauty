import json
import os
import random

from pydub import AudioSegment  # type: ignore
from pydub.playback import play  # type: ignore


class AudioPlayer:
    _instance = None

    def __new__(cls, mappings_file):
        if cls._instance is None:
            cls._instance = super(AudioPlayer, cls).__new__(cls)
            cls._instance._initialize(mappings_file)
        return cls._instance

    def _initialize(self, mappings_file):
        with open(mappings_file, "r") as file:
            self.audio_mappings = json.load(file)

    def play_audio(self, output_string: str):
        audio_files = self.audio_mappings.get(output_string)
        if audio_files:
            audio_file = self._select_weighted_random_file(audio_files)
            if audio_file and os.path.exists(audio_file):
                audio = AudioSegment.from_file(audio_file)
                play(audio)
            else:
                print(f'Audio file "{audio_file}" not found or does not exist.')
        else:
            print(f'No audio files found for "{output_string}".')

    def _select_weighted_random_file(self, audio_files):
        total_weight = sum(file["weight"] for file in audio_files)
        random_choice = random.uniform(0, total_weight)
        current_weight = 0

        for file in audio_files:
            current_weight += file["weight"]
            if current_weight >= random_choice:
                return file["file"]
