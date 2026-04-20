from pydub import AudioSegment

# Load the audio file
sound = AudioSegment.from_file('标准录音 3(1).mp3')

# Convert to mono
sound = sound.set_channels(1)

# Resample to 16000 Hz
sound = sound.set_frame_rate(16000)

# Export the converted file
sound.export('标准录音 3(1)_mono_16k.wav', format='wav')

print('Audio converted successfully!')
print('Channels:', sound.channels)
print('Sample rate:', sound.frame_rate)