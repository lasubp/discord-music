# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Install ffmpeg
RUN apt update && apt install -y --no-install-recommends ffmpeg

# Set the working directory to /app
WORKDIR /app
COPY . /app

# Install pip requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
# EXPOSE 8080

# Run main.py when the container launches
CMD ["python", "main.py"]
