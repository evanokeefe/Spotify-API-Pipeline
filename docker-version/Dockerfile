# Use an official Python runtime as a parent image
FROM python:3.14-rc-bookworm

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the .env file into the container
COPY .env /app/.env

# Set environment variables from the .env file
ENV DB_NAME=${DB_NAME}
ENV DB_USER_NAME=${DB_USER_NAME}
ENV DB_PASSWORD=${DB_PASSWORD}
ENV DB_HOST=${DB_HOST}
ENV CLIENT_ID=${CLIENT_ID}
ENV CLIENT_SECRET=${CLIENT_SECRET}

# Download and install wait-for-it
RUN wget https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh && \
    chmod +x wait-for-it.sh

# Run the Python script when the container starts
CMD ["./wait-for-it.sh", "postgres:5432", "--", "python", "main.py"]
