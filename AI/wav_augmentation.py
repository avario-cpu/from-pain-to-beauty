import os
import numpy as np
import librosa
import soundfile as sf
from pydub import AudioSegment

# Define the directory containing the files
input_directory = ('C:\\Users\\ville\\MyMegaScript\\AI\\data\\hey_robeau'
                   '\\train\\positive\\raw_5s')
output_directory = ('C:\\Users\\ville\\MyMegaScript\\AI\\data\\hey_robeau'
                    '\\train\\positive\\augmented1')

# Create the output directory if it doesn't exist
os.makedirs(output_directory, exist_ok=True)


def add_white_noise(audio, noise_level=0.005):
    noise = np.random.randn(len(audio))
    augmented_audio = audio + noise_level * noise
    return augmented_audio


def pitch_shift(audio, sr, n_steps):
    return librosa.effects.pitch_shift(audio, sr=sr, n_steps=n_steps)


def time_stretch(audio, rate):
    return librosa.effects.time_stretch(audio, rate=rate)


def augment_file(file_path, output_path):
    audio, sr = librosa.load(file_path, sr=None)

    # Apply augmentations
    audio = add_white_noise(audio)
    audio = pitch_shift(audio, sr, np.random.uniform(-2, 2))
    audio = time_stretch(audio, np.random.uniform(0.8, 1.2))

    # Export the augmented file
    sf.write(output_path, audio, sr)


for filename in os.listdir(input_directory):
    if filename.endswith(".wav"):
        input_path = os.path.join(input_directory, filename)
        output_path = os.path.join(output_directory, filename)
        augment_file(input_path, output_path)
        print(f'Augmented {filename}')
