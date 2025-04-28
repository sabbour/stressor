# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy required files into the container at /app
COPY . /app/

# Run stressor.py when the container launches
CMD ["python", "stressor.py"]
