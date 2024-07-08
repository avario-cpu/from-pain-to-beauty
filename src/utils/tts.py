from gtts import gTTS  # type: ignore

# Text to be converted to speech
text = "Hi There!"

# Creating a gTTS object
tts = gTTS(text=text, lang="en", slow=False)

# Saving the speech to a file
output_file = "data\\robeau\\voicelines\\hi_there.mp3"
tts.save(output_file)

print(f"Robotic 'Hello' voice file saved as {output_file}")
