FROM python:3

# Update Software repository
RUN apt-get update
RUN apt install git -y

# Set up dev environment
WORKDIR /bot
RUN git clone https://github.com/Trading-Bot/CryptoBot /bot/cryptobot
WORKDIR /bot/cryptobot
RUN git checkout dev

# install dependencies
RUN bash ./docs/install/linux_installer.sh

# configuration
RUN cp ./config/default_config.json ./config/config.json

# python libs
RUN pip3 install -r requirements.txt

# install evaluators
RUN python3 start.py -p install all

# entry point
ENTRYPOINT ["/python3"]
CMD ["start.py"]
