# Use the official Ubuntu base image
FROM ubuntu:latest

RUN mkdir /app

# Set the working directory to /app
WORKDIR /app

# Update the package list and install Python 3 and pip
RUN apt-get update && \
    apt-get install -y python3 python3-pip

COPY . /app

CMD ["python3", "transform_users.yaml.py"]