FROM tensorflow/tensorflow:2.6.1-gpu

LABEL version="1.0"
LABEL description="Develop clients for Spiking Neural Network models."
LABEL maintainer = "Louis Ross <louis.ross@gmail.com"

WORKDIR /clients

COPY . .

RUN ["python3", "-m", "pip", "install", "-r", "requirements.txt"]

CMD ["bash"]
