import json
import os

import librosa
import librosa.feature
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

POSITIVE_TRAINING_DIR = ('C:\\Users\\ville\\MyMegaScript\\AI\\Robeau\\data'
                         '\\hey_robeau\\train\\positive')
NEGATIVE_TRAINING_DIR = ('C:\\Users\\ville\\MyMegaScript\\AI\\Robeau\\'
                         'data\\hey_robeau\\train\\negative')
TARGET_AUDIO_LENGTH = 5.0
CURRENT_MODEL_SAVE_DIR = ("C:\\Users\\ville\\MyMegaScript\\AI\\Robeau"
                          "\\model_versions\\v0.01")


class AudioDataset(Dataset):
    def __init__(self, positive_dir, negative_dir, target_duration):
        self.positive_dirs = positive_dir
        self.negative_dir = negative_dir
        self.target_duration = target_duration

        self.filepaths = []
        self.labels = []

        self.collect_files_and_labels(positive_dir, label=1)
        self.collect_files_and_labels(negative_dir, label=0)

        print(f"Collected {len(self.filepaths)} files in total.")

        if len(self.filepaths) == 0:
            raise ValueError(
                "No audio files found. Please check the provided directories.")

    def collect_files_and_labels(self, directory, label):
        for root, _, files in os.walk(directory):
            wav_files = [os.path.join(root, file) for file in files if
                         file.endswith('.wav')]
            self.filepaths.extend(wav_files)
            self.labels.extend([label] * len(wav_files))

    def __len__(self):
        return len(self.filepaths)

    def __getitem__(self, idx):
        file_path = self.filepaths[idx]
        audio, sr = librosa.load(file_path, sr=None)
        audio = self.normalize_length(audio, sr, self.target_duration)
        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        mfcc = torch.tensor(mfcc, dtype=torch.float32).flatten()

        label = self.labels[idx]
        return mfcc, label

    @staticmethod
    def normalize_length(audio, sr, target_duration):
        target_length = int(target_duration * sr)
        current_length = len(audio)

        if current_length > target_length:
            audio = audio[:target_length]
        elif current_length < target_length:
            padding = target_length - current_length
            audio = np.pad(audio, (0, padding), mode='constant')

        return audio

    def _generate_labels(self):
        # Replace with actual label generation logic
        labels = []
        for file_path in self.filepaths:
            if "target_phrase" in file_path:
                labels.append(1)
            else:
                labels.append(0)
        return labels


class SimpleLinearModel(nn.Module):
    def __init__(self, input_size):
        super(SimpleLinearModel, self).__init__()
        self.fc1 = nn.Linear(input_size, 128)
        self.fc2 = nn.Linear(128, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        x = self.sigmoid(x)
        return x


def main():
    positive_dir = POSITIVE_TRAINING_DIR
    negative_dir = NEGATIVE_TRAINING_DIR
    target_duration = TARGET_AUDIO_LENGTH
    save_dir = CURRENT_MODEL_SAVE_DIR
    os.makedirs(save_dir, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f'Using device: {device}')

    batch_size = 10
    input_size = 13 * 157  # MFCC shape (13 coefficients, 157 frames)
    criterion = nn.BCELoss()
    learning_rate = 0.001
    model = SimpleLinearModel(input_size).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    dataset = AudioDataset(positive_dir, negative_dir, target_duration)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    num_epochs = 20
    loss_values = []

    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0

        for inputs, labels in dataloader:
            inputs, labels = inputs.to(device), labels.to(device)
            inputs = inputs.view(inputs.size(0), -1)  # Flatten the input
            labels = labels.unsqueeze(
                1).float()  # Ensure labels are float for BCELoss

            optimizer.zero_grad()

            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            print(f'Outputs: {outputs.detach().cpu().numpy()}, '
                  f'Labels: {labels.cpu().numpy()}, Loss: {loss.item()}')

        epoch_loss = running_loss / len(dataset)
        loss_values.append(epoch_loss)
        print(f'Epoch {epoch + 1}/{num_epochs}, Loss: {epoch_loss:.8f}')

    print('Training complete')

    plt.plot(range(1, num_epochs + 1), loss_values, label='Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Training Loss over Epochs')
    plt.legend()

    plot_path = os.path.join(save_dir, "training_loss_plot.png")
    plt.savefig(plot_path)
    print(f"Plot saved to {plot_path}")

    plt.show()

    model_path = os.path.join(save_dir, "audio_classification_model.pth")
    torch.save(model.state_dict(), model_path)
    print(f"Model saved to {model_path}")

    metadata = {
        'positive_dir': positive_dir,
        'negative_dir': negative_dir,
        'target_duration': target_duration,
        'batch_size': batch_size,
        'num_epochs': num_epochs,
        'input_size': input_size,
        'loss_function': 'BCELoss',
        'optimizer': 'Adam',
        'learning_rate': learning_rate,
        'device': str(device),
        'loss_values': loss_values
    }

    metadata_path = os.path.join(save_dir, "training_metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)
    print(f"Training metadata saved to {metadata_path}")


if __name__ == "__main__":
    main()
