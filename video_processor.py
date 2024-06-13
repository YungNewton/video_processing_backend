import os
import re
import logging
import subprocess
import requests
from pathlib import Path
from time import sleep

class VideoProcessor:
    def __init__(self, new_mp3_path, srt_path_new, srt_path_old, video_path, bgm_happy_path, bgm_sad_path, happy_start, happy_end, sad_start, sad_end, bg_width, bg_height, font_size, bottom_padding, max_width, output_dir):
        self.new_mp3_path = Path(new_mp3_path)
        self.srt_path_new = Path(srt_path_new)
        self.srt_path_old = Path(srt_path_old)
        self.video_path = Path(video_path)
        self.bgm_happy_path = Path(bgm_happy_path)
        self.bgm_sad_path = Path(bgm_sad_path)
        self.happy_start = happy_start
        self.happy_end = happy_end
        self.sad_start = sad_start
        self.sad_end = sad_end
        self.bg_width = bg_width
        self.bg_height = bg_height
        self.font_size = font_size
        self.bottom_padding = bottom_padding
        self.max_width = max_width  # New max width attribute
        self.volume_1 = 1.0  # Volume adjustment for happy music
        self.volume_2 = 0.2  # Volume adjustment for sad music
        self.output_dir = Path(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    def run_ffmpeg_command(self, command):
        """
        Run an ffmpeg command and print the output.

        :param command: list - The ffmpeg command to run.
        """
        command = [str(arg) for arg in command]  # Convert all arguments to strings
        print(f"Running ffmpeg command: {' '.join(command)}")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"ffmpeg command failed with error: {result.stderr.decode('utf-8')}")
            raise subprocess.CalledProcessError(result.returncode, command)
        else:
            print(result.stdout.decode('utf-8'))

    def adjust_volume(self, input_path, output_path, volume):
        """
        Adjust the volume of an audio file.

        :param input_path: str - Path to the input audio file.
        :param output_path: str - Path to the output audio file.
        :param volume: float - Volume adjustment factor (e.g., 0.5 for half volume, 2.0 for double volume).
        """
        self.run_ffmpeg_command([
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-filter:a", f"volume={volume}",
            str(output_path)
        ])

    def overlay_audio(self, concatenated_video_path, final_output_path):
        """
        Overlay the audio with background music on the video.

        :param concatenated_video_path: Path - Path to the concatenated video.
        :param final_output_path: Path - Path to the final output video.
        """
        # Trim the first background music file
        trimmed_music_1 = self.output_dir / "trimmed_music_1.wav"
        self.run_ffmpeg_command([
            "ffmpeg", "-y",
            "-i", str(self.bgm_happy_path),
            "-ss", str(self.happy_start),
            "-to", str(self.happy_end),
            "-c:a", "pcm_s16le",
            str(trimmed_music_1)
        ])

        # Trim the second background music file
        trimmed_music_2 = self.output_dir / "trimmed_music_2.wav"
        self.run_ffmpeg_command([
            "ffmpeg", "-y",
            "-i", str(self.bgm_sad_path),
            "-ss", str(self.sad_start),
            "-to", str(self.sad_end),
            "-c:a", "pcm_s16le",
            str(trimmed_music_2)
        ])

        # Adjust volume of the first trimmed music file
        adjusted_volume_music_1 = self.output_dir / "adjusted_volume_music_1.wav"
        self.adjust_volume(trimmed_music_1, adjusted_volume_music_1, self.volume_1)

        # Adjust volume of the second trimmed music file
        adjusted_volume_music_2 = self.output_dir / "adjusted_volume_music_2.wav"
        self.adjust_volume(trimmed_music_2, adjusted_volume_music_2, self.volume_2)

        # Loop the happy and sad music to cover the specified time ranges
        looped_music_1 = self.output_dir / "looped_music_1.wav"
        looped_music_2 = self.output_dir / "looped_music_2.wav"

        self.run_ffmpeg_command([
            "ffmpeg", "-y",
            "-i", str(adjusted_volume_music_1),
            "-filter_complex", f"aloop=loop=-1:size=2e+09,atrim=0:{self.happy_end - self.happy_start}[a]",
            "-map", "[a]",
            "-c:a", "pcm_s16le",
            str(looped_music_1)
        ])

        self.run_ffmpeg_command([
            "ffmpeg", "-y",
            "-i", str(adjusted_volume_music_2),
            "-filter_complex", f"aloop=loop=-1:size=2e+09,atrim=0:{self.sad_end - self.sad_start}[a]",
            "-map", "[a]",
            "-c:a", "pcm_s16le",
            str(looped_music_2)
        ])

        # Concatenate the looped music files
        concatenated_music = self.output_dir / "concatenated_music.wav"
        self.run_ffmpeg_command([
            "ffmpeg", "-y",
            "-i", str(looped_music_1),
            "-i", str(looped_music_2),
            "-filter_complex", "[0:a][1:a]acrossfade=d=0.1[a]",
            "-map", "[a]",
            "-c:a", "pcm_s16le",
            str(concatenated_music)
        ])

        # Combine the looped music with the original video
        self.run_ffmpeg_command([
            "ffmpeg", "-y",
            "-i", str(concatenated_video_path),
            "-i", str(self.new_mp3_path),
            "-i", str(concatenated_music),
            "-filter_complex", "[2:a]volume=1[a2];[1:a]volume=3.5[a1];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            str(final_output_path)
        ])

    def parse_srt(self, srt_path):
        """
        Parse an SRT file to extract timestamps and text.

        :param srt_path: str - Path to the SRT file.
        :return: list of tuples - List of (start_time, end_time, text) tuples.
        """
        subtitles = []  # Initialize the subtitles list
        pattern = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})')
        with open(srt_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            text = ""
            for line in lines:
                line = line.strip()
                matches = pattern.findall(line)
                if matches:
                    if text:
                        subtitles[-1] = (*subtitles[-1], text)
                    start_time = matches[0][0]
                    end_time = matches[0][1]
                    subtitles.append((start_time, end_time))
                    text = ""
                elif line and not line.isdigit():
                    text += " " + line if text else line
            if text:
                subtitles[-1] = (*subtitles[-1], text)
            else:
                # Add an empty string for text if none was found
                if len(subtitles[-1]) == 2:
                    subtitles[-1] = (*subtitles[-1], "")
        
        # Ensure all entries have three elements
        for i in range(len(subtitles)):
            if len(subtitles[i]) < 3:
                subtitles[i] = (*subtitles[i], "")
        
        return subtitles

    @staticmethod
    def srt_time_to_seconds(srt_time):
        """
        Convert SRT time format to seconds.

        :param srt_time: str - Time string in SRT format (H:M:S,mmm).
        :return: float - Time in seconds.
        """
        parts = srt_time.split(":")
        h = int(parts[0])
        m = int(parts[1])
        s_ms = parts[2].split(",")
        s = int(s_ms[0])
        ms = int(s_ms[1])

        total_seconds = h * 3600 + m * 60 + s + ms / 1000.0
        return total_seconds

    def generate_length_for_audios(self):
        new_audio_timestamps = self.parse_srt(self.srt_path_new)
        old_audio_timestamps = self.parse_srt(self.srt_path_old)
        return new_audio_timestamps, old_audio_timestamps

    def compare_timestamps(self, old_timestamps, new_timestamps, tolerance=1e-6):
        if len(old_timestamps) != len(new_timestamps):
            raise ValueError("The number of old and new timestamps must be the same.")
        time_diffs = []
        for (old_start, old_end, _), (new_start, new_end, _) in zip(old_timestamps, new_timestamps):
            old_duration = self.srt_time_to_seconds(old_end) - self.srt_time_to_seconds(old_start)
            new_duration = self.srt_time_to_seconds(new_end) - self.srt_time_to_seconds(new_start)
            time_diff = new_duration - old_duration
            if abs(time_diff) < tolerance:
                time_diff = 0  # Consider negligible differences as zero
            time_diffs.append(time_diff)

        return time_diffs

    def refine_timestamps(self, old_timestamps, time_diffs):
        refined_timestamps = []
        for (start, end, text), time_diff in zip(old_timestamps, time_diffs):
            if time_diff < 0:
                end_seconds = self.srt_time_to_seconds(end)
                end_seconds += time_diff
                end = f"{int(end_seconds // 3600):02}:{int((end_seconds % 3600) // 60):02}:{int(end_seconds % 60):02},{int((end_seconds % 1) * 1000):03}"
            refined_timestamps.append((start, end, text))
        return refined_timestamps

    def trim_video_clips(self, timestamps, time_diffs):
        clips = []
        for i, ((start, end, _), time_diff) in enumerate(zip(timestamps, time_diffs)):
            output_clip = self.output_dir / f"clip_{i}.mp4"
            
            # Default FFmpeg command for trimming
            ffmpeg_command = [
                "ffmpeg", "-y",           # Overwrite output files without asking
                "-i", str(self.video_path), # Input file
                "-ss", f"{self.srt_time_to_seconds(start):.4f}",    # Start time in seconds with four decimal places
                "-to", f"{self.srt_time_to_seconds(end):.4f}",      # End time in seconds with four decimal places
                "-c:v", "libx264",        # Re-encode video using libx264 codec
                "-c:a", "aac",            # Re-encode audio using AAC codec
                str(output_clip)          # Output file
            ]

            # Adjust the FFmpeg command if time_diff is greater than 0
            if time_diff > 0.8:
                # Calculate the original duration
                original_duration = self.srt_time_to_seconds(end) - self.srt_time_to_seconds(start)
                # Calculate the new duration and speed factor
                new_duration = original_duration + time_diff
                speed_factor = original_duration / new_duration

                # Update the FFmpeg command to slow down the clip
                ffmpeg_command = [
                    "ffmpeg", "-y",           # Overwrite output files without asking
                    "-i", str(self.video_path), # Input file
                    "-ss", f"{self.srt_time_to_seconds(start):.4f}",    # Start time in seconds with four decimal places
                    "-to", f"{self.srt_time_to_seconds(end):.4f}",      # End time in seconds with four decimal places
                    "-filter_complex", 
                    f"[0:v]setpts={1/speed_factor}*PTS[v];[0:a]atempo={speed_factor}[a]",
                    "-map", "[v]",
                    "-map", "[a]",
                    "-c:v", "libx264",        # Re-encode video using libx264 codec
                    "-c:a", "aac",            # Re-encode audio using AAC codec
                    str(output_clip)          # Output file
                ]

            try:
                subprocess.run(ffmpeg_command, check=True)  # Run the ffmpeg command
                if os.path.exists(output_clip):             # Check if the output file was created
                    clips.append(output_clip)
                else:
                    logging.error(f"Failed to create clip: {output_clip}")
            except subprocess.CalledProcessError as e:
                logging.error(f"ffmpeg command failed: {e}")
        
        return clips

    def concatenate_clips(self, clips, output_path):
        with open(self.output_dir / "filelist.txt", "w") as file:
            for clip in clips:
                file.write(f"file '{os.path.abspath(clip)}'\n")
        ffmpeg_command = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(self.output_dir / "filelist.txt"),
            "-c", "copy",
            str(output_path)
        ]
        subprocess.run(ffmpeg_command, check=True)
        os.remove(self.output_dir / "filelist.txt")

    def send_to_subtitle_service(self, video_path, srt_path, subtitle_service_url, font_path, font_size, bg_width, bg_height, bottom_padding, max_width, retries=3, wait=10):
        """
        Send video and SRT to subtitle service and return the processed video path.

        :param video_path: Path - Path to the input video file.
        :param srt_path: Path - Path to the SRT file.
        :param subtitle_service_url: str - URL of the subtitle service.
        :param font_path: str - Path to the font file.
        :param font_size: int - Font size for the subtitles.
        :param bg_width: int - Width of the background box.
        :param bg_height: int - Height of the background box.
        :param bottom_padding: int - Padding at the bottom of the background.
        :param max_width: int - Maximum width of the text box before wrapping.
        :param retries: int - Number of retry attempts.
        :param wait: int - Wait time between retries in seconds.
        :return: Path - Path to the processed video with subtitles.
        """
        files = {
            'video': open(video_path, 'rb'),
            'srt': open(srt_path, 'rb')
        }
        data = {
            'font_path': font_path,
            'font_size': font_size,
            'bg_width': bg_width,
            'bg_height': bg_height,
            'bottom_padding': bottom_padding,
            'max_width': max_width  # Include max width in the request data
        }

        for attempt in range(retries):
            try:
                response = requests.post(subtitle_service_url, files=files, data=data, timeout=6000)
                if response.status_code == 200:
                    # Save the received video
                    processed_video_path = self.output_dir / "video_with_subtitles.mp4"
                    with open(processed_video_path, 'wb') as f:
                        f.write(response.content)
                    return processed_video_path
                else:
                    logging.error(f"Failed to receive processed video. Status code: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logging.error(f"Error contacting subtitle service: {e}")

            logging.info(f"Retrying... ({attempt + 1}/{retries})")
            sleep(wait)

        raise Exception("Failed to receive processed video after multiple attempts")

    def process_video(self):
        new_timestamps, old_timestamps = self.generate_length_for_audios()
        print(f"New timestamps: {new_timestamps}")  # Debugging statement
        print(f"Old timestamps: {old_timestamps}")  # Debugging statement
        time_diffs = self.compare_timestamps(old_timestamps, new_timestamps)
        refined_timestamps = self.refine_timestamps(old_timestamps, time_diffs)
        print(f"Refined timestamps: {refined_timestamps}")  # Debugging statement
        trimmed_clips = self.trim_video_clips(refined_timestamps, time_diffs)
        concatenated_video_path = self.output_dir / "concatenated_video.mp4"
        self.concatenate_clips(trimmed_clips, concatenated_video_path)
        
        # Send the video and new SRT to subtitle service
        subtitle_service_url = "https://video-processing-addsubs.chickenkiller.com/add_subtitles"
        subtitled_video_path = self.send_to_subtitle_service(concatenated_video_path, self.srt_path_new, subtitle_service_url, str(self.output_dir / "Montserrat-Bold.ttf"), self.font_size, self.bg_width, self.bg_height, self.bottom_padding, self.max_width)

        final_output_path = self.output_dir / "final_video.mp4"
        self.overlay_audio(subtitled_video_path, final_output_path)

        return final_output_path
