from pydub import AudioSegment
from pydub.silence import detect_nonsilent

class SilenceRemover:
    def __init__(self, silence_threshold=-50.0, min_silence_len=500):
        self.silence_threshold = silence_threshold
        self.min_silence_len = min_silence_len

    def trim_silence(self, audio_path, output_path):
        """
        Trim silence from an audio file.

        :param audio_path: str - Path to the input audio file.
        :param output_path: str - Path to save the trimmed audio file.
        """
        # Load the audio file
        audio = AudioSegment.from_file(audio_path)

        # Detect non-silent chunks
        non_silent_chunks = detect_nonsilent(audio, min_silence_len=self.min_silence_len, silence_thresh=self.silence_threshold)

        # Combine non-silent chunks
        trimmed_audio = AudioSegment.empty()
        for start, end in non_silent_chunks:
            trimmed_audio += audio[start:end]

        # Export the trimmed audio
        trimmed_audio.export(output_path, format="mp3")
        print(f"Trimmed audio saved to: {output_path}")