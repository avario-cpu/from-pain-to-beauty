# inference module

import torch
import librosa
import numpy as np
import sounddevice as sd
from my_model import SimpleNet  # Assume this imports your model definition

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def record_audio(duration=5, fs=16000):
    print("Recording...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1,
                       dtype='float32')
    sd.wait()
    print("Playback...")
    sd.play(recording, fs)
    sd.wait()  # Wait until playback is finished
    return np.squeeze(recording)


def preprocess_audio(audio, target_length=80000, n_mels=128,
                     sampling_rate=16000):
    # If the recording is shorter than the target length, pad it
    if len(audio) < target_length:
        pad_length = target_length - len(audio)
        audio = np.pad(audio, (0, pad_length), mode='constant')
    # If it's longer, trim it
    elif len(audio) > target_length:
        audio = audio[:target_length]

    # Convert audio waveform to Mel spectrogram
    mel_spectrogram = librosa.feature.melspectrogram(y=audio, sr=sampling_rate,
                                                     n_mels=n_mels)
    mel_spectrogram_db = librosa.power_to_db(mel_spectrogram, ref=np.max)

    # Add channel dimension and convert to PyTorch tensor
    mel_spectrogram_db_tensor = torch.tensor(
        mel_spectrogram_db[np.newaxis, np.newaxis, :, :],
        dtype=torch.float).to(device)

    return mel_spectrogram_db_tensor


def load_model(path="my_first_model.pth"):
    model = SimpleNet(input_size=20096, output_size=1).to(device)
    model.load_state_dict(torch.load(path, map_location=device))
    model.eval()
    return model


def predict(model, preprocessed_audio):
    with torch.inference_mode():  # No need to compute gradients
        outputs = model(preprocessed_audio)
        prediction = torch.sigmoid(outputs)
        return prediction.item()


def load_and_preprocess_audio(file_path):
    # Load audio file
    audio, sr = librosa.load(file_path, sr=16000)
    # Preprocess the audio to Mel spectrogram
    return preprocess_audio(audio)


if __name__ == "__main__":
    model = load_model("my_first_model.pth")
    # audio = record_audio(duration=5)  # Record for 5 seconds
    preprocessed_audio = load_and_preprocess_audio("data/test/positive/09.wav")
#     preprocessed_audio = preprocess_audio(audio)
    probability = predict(model, preprocessed_audio)
    print(f"Probability of recognized phrase: {probability}")

    if probability >= 0.5:
        print("Recognized the target phrase!")
    else:
        print("Did not recognize the target phrase.")
