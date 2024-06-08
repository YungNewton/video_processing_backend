import os
import re
import logging
import subprocess
from pathlib import Path

class VideoProcessor:
    def __init__(self, new_mp3_path, srt_path_new, srt_path_old, video_path, bgm_happy_path, bgm_sad_path, happy_start, happy_end, sad_start, sad_end, output_dir):
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
            "-i", input_path,
            "-filter:a", f"volume={volume}",
            output_path
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

        # Concatenate the two trimmed music files with a smooth transition
        concatenated_music = self.output_dir / "concatenated_music.wav"
        self.run_ffmpeg_command([
            "ffmpeg", "-y",
            "-i", str(adjusted_volume_music_1),
            "-i", str(adjusted_volume_music_2),
            "-filter_complex", "[0:a][1:a]acrossfade=d=0.1[a]",
            "-map", "[a]",
            "-c:a", "pcm_s16le",
            str(concatenated_music)
        ])

        # Combine the concatenated music with the original video
        self.run_ffmpeg_command([
            "ffmpeg", "-y",
            "-i", str(concatenated_video_path),
            "-i", str(self.new_mp3_path),
            "-i", str(concatenated_music),
            "-filter_complex", "[2:a]volume=0.3[a2];[1:a][a2]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            str(final_output_path)
        ])

    def parse_srt(self, srt_path):
        timestamps = []
        pattern = re.compile(r'(\d{1,2}:\d{2}:\d{2},\d{3}) --> (\d{1,2}:\d{2}:\d{2},\d{3})')
        with open(srt_path, 'r') as file:
            lines = file.readlines()
            for line in lines:
                matches = pattern.findall(line)
                if matches:
                    start_time = matches[0][0]
                    end_time = matches[0][1]
                    start_ms = self.srt_time_to_seconds(start_time)
                    end_ms = self.srt_time_to_seconds(end_time)
                    timestamps.append((start_ms, end_ms))
        return timestamps

    @staticmethod
    def srt_time_to_seconds(srt_time):
        parts = srt_time.split(":")
        h = float(parts[0])
        m = float(parts[1])
        s_ms = parts[2].split(",")
        s = float(s_ms[0])
        ms = float(s_ms[1])
        ms /= 1000.0
        total_seconds = h * 3600 + m * 60 + s + ms
        return total_seconds

    def generate_length_for_audios(self):
        new_audio_timestamps = self.parse_srt(self.srt_path_new)
        old_audio_timestamps = self.parse_srt(self.srt_path_old)
        return new_audio_timestamps, old_audio_timestamps

    def compare_timestamps(self, old_timestamps, new_timestamps):
        if len(old_timestamps) != len(new_timestamps):
            raise ValueError("The number of old and new timestamps must be the same.")
        time_diffs = []
        for (old_start, old_end), (new_start, new_end) in zip(old_timestamps, new_timestamps):
            old_duration = old_end - old_start
            new_duration = new_end - new_start
            time_diff = new_duration - old_duration
            time_diffs.append(time_diff)
        return time_diffs

    def refine_timestamps(self, old_timestamps, time_diffs):
        refined_timestamps = []
        for (start, end), time_diff in zip(old_timestamps, time_diffs):
            if time_diff < 0:
                end += time_diff
            refined_timestamps.append((start, end))
        return refined_timestamps

    def trim_video_clips(self, timestamps):
        clips = []
        for i, (start, end) in enumerate(timestamps):
            output_clip = self.output_dir / f"clip_{i}.mp4"
            ffmpeg_command = [
                "ffmpeg", "-y",
                "-i", str(self.video_path),
                "-ss", f"{start:.4f}",
                "-to", f"{end:.4f}",
                "-c:v", "libx264",
                "-c:a", "aac",
                str(output_clip)
            ]
            try:
                subprocess.run(ffmpeg_command, check=True)
                if os.path.exists(output_clip):
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

    def process_video(self):
        new_timestamps, old_timestamps = self.generate_length_for_audios()
        time_diffs = self.compare_timestamps(old_timestamps, new_timestamps)
        refined_timestamps = self.refine_timestamps(old_timestamps, time_diffs)
        trimmed_clips = self.trim_video_clips(refined_timestamps)
        concatenated_video_path = self.output_dir / "concatenated_video.mp4"
        self.concatenate_clips(trimmed_clips, concatenated_video_path)
        final_output_path = self.output_dir / "final_video.mp4"
        self.overlay_audio(concatenated_video_path, final_output_path)
        return final_output_path
