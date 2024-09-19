FROM python:3.11-alpine

# Create necessary directories
RUN mkdir -p /usr/src/app/database

# Set working directory
WORKDIR /usr/src/app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Set environment variables
ENV WEBHOOK_URL=""
ENV NITTER_INSTANCE=""
ENV BIRD_USER=""
ENV INTERVAL=""
ENV COLOUR=""

# Run both scripts (use && to run them sequentially)
CMD ["sh", "-c", "python ./birdwatcher.py"]