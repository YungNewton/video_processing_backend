import subprocess
import os

class VideoToAudioConverter:
    def __init__(self):
        pass

    def convert_mp4_to_mp3(self, video_path, output_path):
        """
        Convert an MP4 video file to an MP3 audio file using ffmpeg.
        
        :param video_path: str - Path to the input MP4 file.
        :param output_path: str - Path to save the output MP3 file.
        """
        ffmpeg_command = [
            "ffmpeg", "-y",              # Overwrite output files without asking
            "-i", video_path,            # Input file
            "-q:a", "0",                 # Set audio quality to highest
            "-map", "a",                 # Extract audio track
            output_path                  # Output file
        ]
        subprocess.run(ffmpeg_command, check=True)  # Run the ffmpeg command
        if os.path.exists(output_path):             # Check if the output file was created
            print(f"Successfully created MP3 file: {output_path}")
        else:
            raise Exception(f"Failed to create MP3 file: {output_path}")
