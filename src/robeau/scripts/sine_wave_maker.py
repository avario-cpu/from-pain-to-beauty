from pydub import AudioSegment  # type: ignore
from pydub.generators import Sine  # type: ignore

# Create a sine wave generator with a frequency of 440 Hz (A4 note)
sine_wave = Sine(440)

# Generate a 3-second sine wave
sine_wave_3sec = sine_wave.to_audio_segment(duration=3000)  # duration in milliseconds

sine_wave_3sec = sine_wave_3sec - 10  # decrease volume by 10 decibels

# Save the sine wave as a WAV file
sine_wave_3sec.export(
    "C:\\Users\\ville\\MyMegaScript\\data\\robeau\\voice_lines\\sine.wav", format="wav"
)

print("3-second sine wave file created as 'sine_wave_3sec.wav'")
