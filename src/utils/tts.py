from gtts import gTTS  # type: ignore

# Text to be converted to speech
text = "Ok this is a really really long sentence just to see how you can handle the fact that you would eventually, maybe if all goes get a chance to throw in a message of yours in the meanwhile while im speaking just to see if you are able to cut me off"

# Creating a gTTS object
tts = gTTS(text=text, lang="en", slow=False)

# Saving the speech to a file
output_file = "data\\robeau\\voicelines\\long_sentence.mp3"
tts.save(output_file)

print(f"Robotic 'Hello' voice file saved as {output_file}")
