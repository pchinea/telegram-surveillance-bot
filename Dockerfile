FROM ubuntu:focal
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && \
    apt upgrade -y && \
    apt install -y python3-opencv python3-pip && \
    rm -rf /var/lib/apt/lists/* && \
    pip3 install python-telegram-bot && \
    rm -rf /root/.cache/
WORKDIR /bot
COPY surveillance_bot.py /bot/
COPY surveillance_bot/ /bot/surveillance_bot/
ENTRYPOINT ["python3", "surveillance_bot.py"]