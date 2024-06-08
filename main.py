import os
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pathlib import Path
from tempfile import TemporaryDirectory
from audio_generator import AudioGenerator
from silence_remover import SilenceRemover
from video_to_audio_converter import VideoToAudioConverter
from run_aeneas import RunAeneas
from utils import save_uploaded_file
import zipfile

app = Flask(__name__)
CORS(app)

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        print("Received request")
        text_file = request.files['text']
        video_file = request.files['video']
        voice_id = request.form.get('voice_id')
        api_key = request.form.get('api_key')
        speed = float(request.form.get('speed', 1.15))
        set_speed_up = request.form.get('set_speed_up') == 'on'

        print(f"Text file: {text_file.filename}, Video file: {video_file.filename}, Voice ID: {voice_id}, API Key: {api_key}, Speed: {speed}, Set Speed Up: {set_speed_up}")

        audio_generator = AudioGenerator(api_key, speed, set_speed_up)
        silence_remover = SilenceRemover()
        video_to_audio_converter = VideoToAudioConverter()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            text_path = temp_path / text_file.filename
            video_path = temp_path / video_file.filename
            save_uploaded_file(text_file, text_path)
            save_uploaded_file(video_file, video_path)

            extracted_audio_path = video_path.with_suffix('.mp3')
            generated_audio_path = text_path.with_suffix('.gen.mp3')
            trimmed_audio_path = text_path.with_suffix('.trimmed.mp3')

            video_to_audio_converter.convert_mp4_to_mp3(video_path, extracted_audio_path)
            audio_generator.generate_audio(text_path, generated_audio_path, voice_id)
            silence_remover.trim_silence(generated_audio_path, trimmed_audio_path)

            # Prepare input pairs for RunAeneas
            input_pairs = [
                (trimmed_audio_path, text_path),
                (extracted_audio_path, text_path)
            ]

            # Create and run RunAeneas instance
            run_aeneas = RunAeneas(input_pairs)
            run_aeneas.run()

            # Collect the generated SRT files
            new_timestamps_srt = text_path.with_suffix('_with_timestamps.srt')
            old_timestamps_srt = text_path.with_suffix('.srt')  # Assuming the second generated file uses this pattern

            # Zip the SRT files
            zip_path = temp_path / "srt_files.zip"
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.write(new_timestamps_srt, new_timestamps_srt.name)
                zf.write(old_timestamps_srt, old_timestamps_srt.name)

            return send_file(zip_path, as_attachment=True, download_name="srt_files.zip")

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
