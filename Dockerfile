FROM ubuntu:22.04
RUN apt update &&     apt install -y python-is-python3 python3-pip &&     apt-get install -y git
RUN pip install git+https://github.com/simon-weber/gpsoauth.git@8a5212481f80312e06ba6e0a29fbcfca1f210fd1
