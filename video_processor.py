import os
import re
import logging
import subprocess
from pathlib import Path

class VideoProcessor:
    def __init__(self, new_mp3_path, srt_path_new, srt_path_old, video_path, bgm_choice, output_dir):
        self.new_mp3_path = Path(new_mp3_path)
        self.srt_path_new = Path(srt_path_new)
        self.srt_path_old = Path(srt_path_old)
        self.video_path = Path(video_path)
        self.bgm_choice = Path(bgm_choice)
        self.output_dir = Path(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

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

    def overlay_audio(self, concatenated_video_path, final_output_path, bgm_track_path):
        ffmpeg_command = [
            "ffmpeg", "-y",
            "-i", str(concatenated_video_path),
            "-i", str(self.new_mp3_path),
            "-i", str(bgm_track_path),
            "-filter_complex", "[2:a]volume=0.2[a2];[1:a][a2]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            str(final_output_path)
        ]
        try:
            result = subprocess.run(ffmpeg_command, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            logging.debug(f"ffmpeg stdout: {result.stdout.decode('utf-8')}")
        except subprocess.CalledProcessError as e:
            logging.error(f"ffmpeg command failed with error: {e.stderr.decode('utf-8')}")
            raise

    def process_video(self):
        new_timestamps, old_timestamps = self.generate_length_for_audios()
        time_diffs = self.compare_timestamps(old_timestamps, new_timestamps)
        refined_timestamps = self.refine_timestamps(old_timestamps, time_diffs)
        trimmed_clips = self.trim_video_clips(refined_timestamps)
        concatenated_video_path = self.output_dir / "concatenated_video.mp4"
        self.concatenate_clips(trimmed_clips, concatenated_video_path)
        final_output_path = self.output_dir / "final_video.mp4"
        self.overlay_audio(concatenated_video_path, final_output_path, self.bgm_choice)
        return final_output_path
