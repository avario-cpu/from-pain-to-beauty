import os
import numpy as np
import librosa
import torch
from torch.utils.data import Dataset, DataLoader

import torch.nn as nn


class AudioDataset(Dataset):
    def __init__(self, directory, target_duration=1.0,
                 target_phrase="Hey Robo"):
        self.directory = directory
        self.target_duration = target_duration
        self.filepaths = [os.path.join(directory, fname) for fname in
                          os.listdir(directory) if fname.endswith('.wav')]
        self.labels = self._generate_labels()
        # Generate labels based on your data

    def __len__(self):
        return len(self.filepaths)

    def __getitem__(self, idx):
        file_path = self.filepaths[idx]
        audio, sr = librosa.load(file_path, sr=None)
        audio = self.normalize_length(audio, sr, self.target_duration)
        mfccs = librosa.feature.mfcc(audio, sr=sr, n_mfcc=13)
        mfccs = torch.tensor(mfccs,
                             dtype=torch.float32).flatten()
        # Flatten the MFCCs for linear model

        label = self.labels[idx]
        return mfccs, label

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


# Create dataset and dataloader
dataset = AudioDataset('C:\\Users\\ville\\MyMegaScript\\AI\\data\\hey_robeau'
                       '\\train\\positive\\raw_5s')
dataloader = DataLoader(dataset, batch_size=32, shuffle=True)


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


# Example input size: 13 MFCCs * number of frames (e.g., 13 * 44 = 572)
input_size = 13 * 44  # Adjust based on your MFCC extraction
model = SimpleLinearModel(input_size)

criterion = nn.BCELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

num_epochs = 20

for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0

    for inputs, labels in dataloader:
        inputs = inputs.view(inputs.size(0), -1)  # Flatten the input
        labels = labels.unsqueeze(
            1).float()  # Ensure labels are float for BCELoss

        optimizer.zero_grad()

        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * inputs.size(0)

    epoch_loss = running_loss / len(dataloader.dataset)
    print(f'Epoch {epoch + 1}/{num_epochs}, Loss: {epoch_loss:.4f}')

print('Training complete')
