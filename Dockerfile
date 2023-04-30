FROM python AS builder

RUN apt-get update && apt-get -y upgrade

RUN apt install -y ffmpeg

RUN pip install -U kodekloud-downloader


FROM builder

CMD kodekloud dl -o /home/kodekloud -c /home/kodekloud/kodekloud.com_cookies.txt -q 1080p

