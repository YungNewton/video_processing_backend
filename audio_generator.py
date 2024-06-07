import requests
from pathlib import Path
from pydub import AudioSegment

class AudioGenerator:
    def __init__(self, api_key: str, speed: float = 1.15, set_speed_up: bool = True):
        self.api_key = api_key
        self.speed = speed
        self.set_speed_up = set_speed_up
        self.chunk_size = 1024

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
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        response = requests.post(url, json=data, headers=headers)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=self.chunk_size):
                if chunk:
                    f.write(chunk)

        if self.set_speed_up:
            self.speed_up_audio_file(output_path)