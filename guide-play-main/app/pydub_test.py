from pydub import AudioSegment


def detect_leading_silence(sound, silence_threshold=-80.0, chunk_size=10):
    '''
    sound is a pydub.AudioSegment
    silence_threshold in dB
    chunk_size in ms

    iterate over chunks until you find the first one with sound
    '''
    trim_ms = 0  # ms

    assert chunk_size > 0  # to avoid infinite loop
    while sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold and trim_ms < len(sound):
        trim_ms += chunk_size

    return trim_ms


def trimSilence(sound):
    start_trim = detect_leading_silence(sound)
    end_trim = detect_leading_silence(sound.reverse())

    duration = len(sound)
    trimmed_sound = sound[start_trim:duration-end_trim]

    return trimmed_sound


def addSilence(sound, duration):
    # sound = AudioSegment.from_wav(input_wav_file)
    silence = AudioSegment.silent(duration=duration)
    combined = sound + silence
    return combined


def concatenateSound(sound, times):
    combined_segment = sound
    for i in range(times):
        combined_segment += sound
    return combined_segment


trimmed_sound = trimSilence(AudioSegment.from_wav(
    "sounds/beep_enemy0.wav"))

output_wav_file = "sounds/beep_enemy0_trimmed_5s.wav"
output_wav_file_combined = "sounds/beep_enemy0_trimmed_5times.wav"

combined_segment = addSilence(trimmed_sound, 0.5)
combined_segment.export(output_wav_file, format="wav")

concatenated = concatenateSound(combined_segment, 5)
concatenated.export(output_wav_file_combined, format="wav")
