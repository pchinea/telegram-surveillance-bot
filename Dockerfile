FROM python:3.8
WORKDIR /bot
COPY requirements.txt src/ /bot/
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "main.py"]