FROM debian:bullseye-slim
ENV PORT=${PORT}
EXPOSE ${PORT}
RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install python3-pip -y
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
RUN pip install gunicorn
CMD gunicorn -b 0.0.0.0:${PORT} app:app