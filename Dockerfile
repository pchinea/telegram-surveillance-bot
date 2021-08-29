FROM ubuntu:focal
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y python3-opencv python3-pip && \
    rm -rf /var/lib/apt/lists/* && \
    pip3 install "python-telegram-bot>=13,<14" && \
    rm -rf /root/.cache/
WORKDIR /bot
COPY start.py /bot/
COPY surveillance_bot/ /bot/surveillance_bot/
ENTRYPOINT ["python3", "start.py"]