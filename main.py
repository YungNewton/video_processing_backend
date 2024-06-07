import os
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pathlib import Path
from tempfile import TemporaryDirectory
from audio_generator import AudioGenerator
from utils import save_uploaded_file

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Get the uploaded files and form data
        text_file = request.files['text']
        voice_id = request.form.get('voice_id')
        api_key = request.form.get('api_key')
        speed = float(request.form.get('speed', 1.15))
        set_speed_up = request.form.get('set_speed_up', 'true').lower() == 'true'

        # Create an instance of AudioGenerator
        audio_generator = AudioGenerator(api_key, speed, set_speed_up)

        # Create a temporary directory to save the files
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Save the uploaded text file
            text_path = temp_path / text_file.filename
            save_uploaded_file(text_file, text_path)

            # Define the output audio file path
            output_path = text_path.with_suffix('.mp3')

            # Generate the audio file
            audio_generator.generate_audio(text_path, output_path, voice_id)

            # Return the generated audio file to the client
            return send_file(output_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
