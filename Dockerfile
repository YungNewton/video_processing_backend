# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies and build tools
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak \
    libespeak-dev \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Clone the aeneas repository
RUN git clone https://github.com/readbeyond/aeneas.git /app/aeneas

# Change to the aeneas directory and install Python dependencies
WORKDIR /app/aeneas
RUN python3 -m pip install -r requirements.txt

# Install aeneas
RUN python3 setup.py install

# Change back to the app directory
WORKDIR /app

# Install Flask and other Python dependencies
COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

# Copy background music files
COPY happy.mp3 /app/
COPY sad.mp3 /app/

# Run the script when the container launches
CMD ["python3", "main.py"]
