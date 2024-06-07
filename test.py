import requests
from pathlib import Path
from pydub import AudioSegment

# Configuration
API_KEY = "d3292ba871ea921bc47ca14ebb5566db"
VOICE_ID = "VJGiea1BxPRl3hHnzsxe"
SET_SPEED_UP = True
SPEED = 1.15
CHUNK_SIZE = 1024

def read_text_file(file_path: Path) -> str:
    if not file_path.is_file():
        raise Exception(f"{file_path}: NOT a file.")
    if file_path.suffix != ".txt":
        raise Exception(f"{file_path}: File is NOT a plain text file (.txt). Please provide a plain text file.")
    with open(file_path, "r") as f:
        text = f.read()
    return text

def speed_up_audio_file(file_path):
    audio = AudioSegment.from_file(file_path)
    sped_up_audio = audio.speedup(playback_speed=SPEED)
    sped_up_audio.export(file_path, format="mp3")

def generate_audio(text_path: Path, output_path: Path):
    text = read_text_file(text_path)
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": API_KEY
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
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)

    if SET_SPEED_UP:
        speed_up_audio_file(output_path)

def main():
    text_file_path = input("Enter the path to the text file: ")
    text_path = Path(text_file_path)
    if not text_path.is_file():
        print(f"{text_path} is not a valid file.")
        return

    output_path = text_path.with_suffix('.mp3')
    generate_audio(text_path, output_path)
    print(f"Audio generated and saved to {output_path}")

if __name__ == "__main__":
    main()
