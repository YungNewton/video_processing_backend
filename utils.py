from pathlib import Path

def save_uploaded_file(upload, destination):
    upload.save(destination)

def create_temp_directory(tempfile):
    return Path(tempfile.TemporaryDirectory().name)
