FROM python:3.9-slim
WORKDIR /backend
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
RUN touch /backend/scheduler.log
RUN apt-get update
RUN apt-get -y install procps vim
CMD ["python", "/backend/scheduler.py"]
