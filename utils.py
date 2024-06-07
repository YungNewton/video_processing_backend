from pathlib import Path

def save_uploaded_file(uploaded_file, destination: Path):
    with destination.open('wb') as f:
        f.write(uploaded_file.read())

