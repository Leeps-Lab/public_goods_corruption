# Install of dependencies
FROM ubuntu:22.04 AS builder

RUN apt update && apt upgrade -y
RUN apt install software-properties-common -y
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt install -y python3.10
RUN python3.10 --version

RUN apt-get update && apt-get install -y python3-pip

RUN python3 -m pip install -U otree


# Set the working directory in the container
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . /app

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run oTree when the container launches
CMD ["otree", "prodserver", "8000"]