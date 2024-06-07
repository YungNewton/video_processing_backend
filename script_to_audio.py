from pathlib import Path
from elevenlabs.client import ElevenLabs
from elevenlabs import save
from pydub import AudioSegment

class AudioGenerator:
    def __init__(self, api_key: str, speed: float, set_speed_up: bool):
        self.api_key = api_key
        self.speed = speed
        self.set_speed_up = set_speed_up
        self.client = ElevenLabs(api_key=api_key)

    def read_text_file(self, file_path: Path) -> str:
        if not file_path.is_file():
            raise Exception(f"{file_path}: NOT a file.")
        if file_path.suffix != ".txt":
            raise Exception(f"{file_path}: File is NOT a plain text file (.txt). Please provide a plain text file.")
        with open(file_path, "r") as f:
            text = f.read()
        return text

    def speed_up_audio_file(self, file_path):
        audio = AudioSegment.from_file(file_path)
        sped_up_audio = audio.speedup(playback_speed=self.speed)
        sped_up_audio.export(file_path, format="mp3")

    def generate_audio(self, text_path: Path, output_path: Path, voice_id: str):
        text = self.read_text_file(text_path)
        audio = self.client.generate(text=text, voice_id=voice_id)
        save(audio, output_path)
        if self.set_speed_up:
            self.speed_up_audio_file(output_path)
