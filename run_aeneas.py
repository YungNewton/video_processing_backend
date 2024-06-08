import os
import subprocess
import json

class RunAeneas:
    def __init__(self, input_pairs):
        self.input_pairs = input_pairs

    def generate_sync_map(self, mp3_file, txt_file, output_file_path):
        command = f'python3 -m aeneas.tools.execute_task "{mp3_file}" "{txt_file}" "task_language=eng|is_text_type=plain|os_task_file_format=json" "{output_file_path}"'
        print("Running command:", command)
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Check the output and error of the command
        print("Command output:", result.stdout.decode('utf-8'))
        print("Command error:", result.stderr.decode('utf-8'))

        # Verify if the output file was created
        if not os.path.exists(output_file_path):
            raise FileNotFoundError(f"The output file {output_file_path} was not created. Check the command output above for errors.")

    def read_output_file(self, output_file_path):
        with open(output_file_path, 'r') as f:
            return json.load(f)

    def convert_time(self, seconds):
        milliseconds = int((seconds - int(seconds)) * 1000)
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

    def process_output(self, sync_map, txt_file):
        aligned_output = []
        for index, fragment in enumerate(sync_map['fragments']):
            start = self.convert_time(float(fragment['begin']))
            end = self.convert_time(float(fragment['end']))
            text = fragment['lines'][0].strip()
            aligned_output.append(f"{index + 1}\n{start} --> {end}\n{text}\n")

        srt_file = txt_file.replace(".txt", "_with_timestamps.srt")
        with open(srt_file, 'w') as file:
            for line in aligned_output:
                file.write(line + "\n")

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

        srt_json_file = srt_file.replace(".srt", ".json")
        with open(srt_json_file, 'w') as file:
            json.dump(srt_json, file, indent=4)

        return srt_file, srt_json_file

    def run(self):
        for mp3_file, txt_file in self.input_pairs:
            if not os.path.isfile(mp3_file) or not os.path.isfile(txt_file):
                raise ValueError(f"MP3 and TXT files are required: {mp3_file}, {txt_file}")

            output_file_path = txt_file.replace(".txt", "_aligned.json")
            self.generate_sync_map(mp3_file, txt_file, output_file_path)
            sync_map = self.read_output_file(output_file_path)
            srt_file, srt_json_file = self.process_output(sync_map, txt_file)
            print(f"Output files created: {srt_file}, {srt_json_file}")
