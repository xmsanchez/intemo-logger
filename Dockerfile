FROM python:slim-bullseye

RUN apt update && apt install -y wget

# Install Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install

RUN mkdir /app

WORKDIR /app

COPY requirements.txt /app

RUN pip install -r requirements.txt

COPY main.py /app

ENTRYPOINT ["python", "main.py"]
