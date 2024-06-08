import os
import subprocess
import json
import logging

class RunAeneas:
    def __init__(self, input_pairs):
        self.input_pairs = input_pairs
        logging.basicConfig(level=logging.DEBUG)
        logging.debug(f"Initialized RunAeneas with input pairs: {self.input_pairs}")

    def generate_sync_map(self, mp3_file, txt_file, output_file_path):
        command = f'python3 -m aeneas.tools.execute_task "{mp3_file}" "{txt_file}" "task_language=eng|is_text_type=plain|os_task_file_format=json" "{output_file_path}"'
        logging.debug(f"Running command: {command}")
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Check the output and error of the command
        logging.debug("Command output: %s", result.stdout.decode('utf-8'))
        logging.debug("Command error: %s", result.stderr.decode('utf-8'))

        # Verify if the output file was created
        if not os.path.exists(output_file_path):
            raise FileNotFoundError(f"The output file {output_file_path} was not created. Check the command output above for errors.")
        logging.debug(f"Sync map generated successfully: {output_file_path}")

    def read_output_file(self, output_file_path):
        logging.debug(f"Reading output file: {output_file_path}")
        with open(output_file_path, 'r') as f:
            return json.load(f)

    def convert_time(self, seconds):
        milliseconds = int((seconds - int(seconds)) * 1000)
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

    def process_output(self, sync_map, txt_file, srt_file_name):
        logging.debug(f"Processing sync map for: {txt_file}")
        aligned_output = []
        for index, fragment in enumerate(sync_map['fragments']):
            start = self.convert_time(float(fragment['begin']))
            end = self.convert_time(float(fragment['end']))
            text = fragment['lines'][0].strip()
            aligned_output.append(f"{index + 1}\n{start} --> {end}\n{text}\n")

        srt_file = txt_file.with_stem(txt_file.stem + f"_{srt_file_name}").with_suffix(".srt")
        with open(srt_file, 'w') as file:
            for line in aligned_output:
                file.write(line + "\n")
        logging.debug(f"SRT file created: {srt_file}")

        srt_json = []
        for index, fragment in enumerate(sync_map['fragments']):
            start = float(fragment['begin'])
            end = float(fragment['end'])
            text = fragment['lines'][0].strip()
            srt_json.append({
                "index": index + 1,
                "start": start,
                "end": end,
                "text": text
            })

        srt_json_file = srt_file.with_suffix(".json")
        with open(srt_json_file, 'w') as file:
            json.dump(srt_json, file, indent=4)
        logging.debug(f"SRT JSON file created: {srt_json_file}")

        return srt_file, srt_json_file

    def run(self):
        for index, (mp3_file, txt_file) in enumerate(self.input_pairs):
            logging.debug(f"Processing pair: MP3: {mp3_file}, TXT: {txt_file}")
            if not os.path.isfile(mp3_file) or not os.path.isfile(txt_file):
                raise ValueError(f"MP3 and TXT files are required: {mp3_file}, {txt_file}")

            output_file_path = txt_file.with_stem(txt_file.stem + f"_aligned_{index}").with_suffix(".json")
            logging.debug(f"Output file path: {output_file_path}")
            self.generate_sync_map(mp3_file, txt_file, output_file_path)
            sync_map = self.read_output_file(output_file_path)
            srt_file_name = "new_timestamps" if index == 0 else "old_timestamps"
            srt_file, srt_json_file = self.process_output(sync_map, txt_file, srt_file_name)
            logging.debug(f"Output files created: {srt_file}, {srt_json_file}")
