import os
import logging
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from audio_generator import AudioGenerator
from silence_remover import SilenceRemover
from video_to_audio_converter import VideoToAudioConverter
from run_aeneas import RunAeneas
from utils import save_uploaded_file
from video_processor import VideoProcessor
import zipfile

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

logging.basicConfig(level=logging.DEBUG)

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        logging.debug("Received request")

        # Get the uploaded files and form data
        text_file = request.files.get('text')
        video_file = request.files.get('video')
        voice_id = request.form.get('voice_id')
        api_key = request.form.get('api_key')
        speed = request.form.get('speed')
        set_speed_up = request.form.get('set_speed_up')
        bgm_choice = request.form.get('bgm_choice', 'sad')

        if not text_file:
            logging.debug("No text file uploaded")
        if not video_file:
            logging.debug("No video file uploaded")
        if not voice_id:
            logging.debug("No voice_id provided")
        if not api_key:
            logging.debug("No api_key provided")

        speed = float(speed) if speed else 1.15
        set_speed_up = set_speed_up == 'on'  # Interpret checkbox value correctly

        logging.debug(f"Text file: {text_file.filename if text_file else 'None'}")
        logging.debug(f"Video file: {video_file.filename if video_file else 'None'}")
        logging.debug(f"Voice ID: {voice_id}, API Key: {api_key}, Speed: {speed}, Set Speed Up: {set_speed_up}, BGM Choice: {bgm_choice}")

        # Create instances of AudioGenerator, SilenceRemover, and VideoToAudioConverter
        audio_generator = AudioGenerator(api_key, speed, set_speed_up)
        silence_remover = SilenceRemover()
        video_to_audio_converter = VideoToAudioConverter()

        # Create a temporary directory to save the files
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Save the uploaded text and video files
            text_path = temp_path / text_file.filename
            video_path = temp_path / video_file.filename
            save_uploaded_file(text_file, text_path)
            save_uploaded_file(video_file, video_path)

            logging.debug(f"Saved text file to {text_path}")
            logging.debug(f"Saved video file to {video_path}")

            # Verify files exist after saving
            if not os.path.exists(text_path):
                logging.error(f"Text file does not exist after saving: {text_path}")
            if not os.path.exists(video_path):
                logging.error(f"Video file does not exist after saving: {video_path}")

            # Define the output audio file paths
            extracted_audio_path = video_path.with_suffix('.mp3')
            generated_audio_path = text_path.with_suffix('.gen.mp3')
            trimmed_audio_path = text_path.with_suffix('.trimmed.mp3')

            # Convert the video to audio
            video_to_audio_converter.convert_mp4_to_mp3(video_path, extracted_audio_path)
            logging.debug(f"Extracted audio path: {extracted_audio_path}")

            # Verify extracted audio file exists
            if not os.path.exists(extracted_audio_path):
                logging.error(f"Extracted audio file does not exist: {extracted_audio_path}")

            # Generate the audio file from the text
            audio_generator.generate_audio(text_path, generated_audio_path, voice_id)
            logging.debug(f"Generated audio path: {generated_audio_path}")

            # Verify generated audio file exists
            if not os.path.exists(generated_audio_path):
                logging.error(f"Generated audio file does not exist: {generated_audio_path}")

            # Trim silence from the generated audio file
            silence_remover.trim_silence(generated_audio_path, trimmed_audio_path)
            logging.debug(f"Trimmed audio path: {trimmed_audio_path}")

            # Verify trimmed audio file exists
            if not os.path.exists(trimmed_audio_path):
                logging.error(f"Trimmed audio file does not exist: {trimmed_audio_path}")

            # Copy background music files to the temporary directory
            bgm_path = temp_path / f"{bgm_choice}.mp3"
            copyfile(Path(__file__).parent / f"{bgm_choice}.mp3", bgm_path)

            # Prepare input pairs for RunAeneas
            input_pairs = [
                (trimmed_audio_path, text_path),  # Use the silence-removed audio first
                (extracted_audio_path, text_path)  # Use the audio extracted from the video second
            ]

            # Create and run RunAeneas instance
            run_aeneas = RunAeneas(input_pairs)
            run_aeneas.run()

            # Collect the generated SRT files
            new_timestamps_srt = text_path.with_stem(text_path.stem + '_new_timestamps').with_suffix('.srt')
            old_timestamps_srt = text_path.with_stem(text_path.stem + '_old_timestamps').with_suffix('.srt')

            logging.debug(f"New timestamps SRT: {new_timestamps_srt}")
            logging.debug(f"Old timestamps SRT: {old_timestamps_srt}")

            # Verify SRT files exist
            if not os.path.exists(new_timestamps_srt):
                logging.error(f"New timestamps SRT file does not exist: {new_timestamps_srt}")
            if not os.path.exists(old_timestamps_srt):
                logging.error(f"Old timestamps SRT file does not exist: {old_timestamps_srt}")

            # Create and run VideoProcessor instance
            video_processor = VideoProcessor(
                new_mp3_path=trimmed_audio_path,
                srt_path_new=new_timestamps_srt,
                srt_path_old=old_timestamps_srt,
                video_path=video_path,
                bgm_choice=bgm_choice,
                output_dir=temp_path
            )
            final_video_path = video_processor.process_video()

            # Zip the SRT files, the silence-removed audio, and the final video
            zip_path = temp_path / "output_files.zip"
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.write(new_timestamps_srt, new_timestamps_srt.name)
                zf.write(old_timestamps_srt, old_timestamps_srt.name)
                zf.write(trimmed_audio_path, trimmed_audio_path.name)  # Add the silence-removed audio
                zf.write(final_video_path, final_video_path.name)  # Add the final video

            logging.debug(f"Zipped output files: {zip_path}")

            return send_file(zip_path, as_attachment=True, download_name="output_files.zip")

    except Exception as e:
        logging.debug(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logging.debug("Starting Flask app")
    app.run(host='0.0.0.0', port=5000, debug=True)