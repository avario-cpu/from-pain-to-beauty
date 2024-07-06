import os
import numpy as np
import librosa
import soundfile as sf


def normalize_length(audio, sr, target_duration):
    target_length = int(target_duration * sr)
    current_length = len(audio)

    if current_length > target_length:
        # Trim audio
        audio = audio[:target_length]
    elif current_length < target_length:
        # Pad audio
        padding = target_length - current_length
        audio = np.pad(audio, (0, padding), mode='constant')

    return audio


def process_files(input_directory, output_directory, target_duration):
    # Create the output directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)

    for filename in os.listdir(input_directory):
        if filename.endswith(".wav"):
            input_path = os.path.join(input_directory, filename)
            output_path = os.path.join(output_directory, filename)

            audio, sr = librosa.load(input_path, sr=None)
            normalized_audio = normalize_length(audio, sr, target_duration)

            # Save the normalized audio file
            sf.write(output_path, normalized_audio, sr)
            print(f'Processed {filename}')


# Define directories and target duration in seconds
input_directory = ('C:\\Users\\ville\\MyMegaScript\\AI\\data\\hey_robeau'
                   '\\train\\positive\\augmented1')
output_directory = ('C:\\Users\\ville\\MyMegaScript\\AI\\data\\hey_robeau'
                    '\\train\\positive\\augmented1_5s')
target_duration = 5.0  # Set target duration in seconds

process_files(input_directory, output_directory, target_duration)
