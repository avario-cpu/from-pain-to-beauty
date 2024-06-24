import os

import librosa
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision.transforms import ToTensor

# Parameters
SAMPLING_RATE = 16000
N_MELS = 128
BATCH_SIZE = 32
EPOCHS = 1000
TARGET_LENGTH = 16000 * 5

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")


def preprocess_audio(file_path, target_length=TARGET_LENGTH):
    audio, sr = librosa.load(file_path, sr=SAMPLING_RATE)
    # If the file is shorter than the target length, pad it with zeros
    if len(audio) < target_length:
        pad_length = target_length - len(audio)
        audio = np.pad(audio, (0, pad_length), mode='constant')
    # If the file is longer than the target length, trim it
    else:
        audio = audio[:target_length]
    return audio


def load_data(dataset_path):
    X, y = [], []
    for folder_name in ["positive", "negative"]:
        folder_path = os.path.join(dataset_path, folder_name)
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            audio = preprocess_audio(file_path, TARGET_LENGTH)
            audio = np.array(audio)
            mel_spectrogram = librosa.feature.melspectrogram(y=audio,
                                                             sr=SAMPLING_RATE,
                                                             n_mels=N_MELS)
            mel_spectrogram = librosa.power_to_db(mel_spectrogram, ref=np.max)
            X.append(mel_spectrogram[..., np.newaxis])  # Add channel dimension
            y.append(1 if folder_name == "positive" else 0)
    return np.array(X), np.array(y)


class AudioDataset(Dataset):
    def __init__(self, X, y, transform=None):
        self.X = X
        self.y = y
        self.transform = transform

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        sample = self.X[idx]
        label = self.y[idx]
        if self.transform:
            sample = self.transform(sample)
        return sample, label


# Assuming your dataset is organized with 'positive' and 'negative' subfolders
base_path = 'data'
train_dataset_path = os.path.join(base_path, 'train')
test_dataset_path = os.path.join(base_path, 'test')

X_train, y_train = load_data(train_dataset_path)
X_test, y_test = load_data(test_dataset_path)

train_dataset = AudioDataset(X_train, y_train, transform=ToTensor())
test_dataset = AudioDataset(X_test, y_test, transform=ToTensor())

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)


# Model definition
class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1)
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2, padding=0)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)
        self.dropout = nn.Dropout(0.25)

        # Calculate the correct size based on the output shape
        # from the last convolutional layer (64 channels, 32x39 feature map)
        # Adjusted based on the printed shape
        self.fc1 = nn.Linear(64 * (N_MELS // 4) * 39, 128)
        self.fc2 = nn.Linear(128, 1)

    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        # Adjust the flattening according to your input shape
        x = x.view(-1, 64 * (N_MELS // 4) * 39)
        x = torch.relu(self.fc1(self.dropout(x)))
        x = torch.sigmoid(self.fc2(x))
        return x


class SimpleNet(nn.Module):
    def __init__(self, input_size=20096, output_size=1):
        super(SimpleNet, self).__init__()
        self.flatten = nn.Flatten()
        self.linear = nn.Linear(input_size, output_size)

    def forward(self, x):
        x = self.flatten(x)
        x = self.linear(x)
        return x


model = SimpleNet().to(device)
# model = Net().to(device)

criterion = nn.BCEWithLogitsLoss()
optimizer = optim.Adam(model.parameters(), lr=0.00001)


# Training
def train_model():
    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        for inputs, labels in train_loader:
            inputs, labels = (inputs.to(device),
                              labels.to(device).float().unsqueeze(1))  # Move
            # data to GPU

            # Adjust labels' shape for BCEWithLogitsLoss

            optimizer.zero_grad()

            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
        print(f"Epoch {epoch + 1}, Loss: {running_loss / len(train_loader)}")


def test_model():
    # Testing
    model.eval()
    total = 0
    correct = 0
    with torch.inference_mode():
        for inputs, labels in test_loader:
            inputs, labels = inputs.to(device), \
                labels.to(device).float().unsqueeze(1)  # Move data to GPU
            outputs = model(inputs)
            predicted = torch.round(torch.sigmoid(outputs))
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    print(
        f'Accuracy of the model on the test samples: {100 * correct / total}%')


if __name__ == "__main__":
    train_model()
    test_model()
    torch.save(model.state_dict(), "my_first_model.pth")
