# Install of dependencies
FROM ubuntu:22.04 AS builder

# Bootstrap: this base image ships gpgv but not the full gnupg package,
# so apt-key (used internally for InRelease signature verification) fails
# with a misleading "invalid signature" error. Do one insecure update to
# fetch gnupg itself, then a normal (verified) update/upgrade.
RUN apt-get update -o Acquire::AllowInsecureRepositories=true \
    && apt-get install -y --allow-unauthenticated gnupg dirmngr ca-certificates \
    && apt-get update && apt-get upgrade -y
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
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . /app

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run oTree when the container launches
CMD ["otree", "prodserver", "8000"]