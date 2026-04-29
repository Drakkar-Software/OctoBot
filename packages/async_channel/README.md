# Async-Channel
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/523d43c62f1d4de08395752367f5fddc)](https://www.codacy.com/gh/Drakkar-Software/Async-Channel/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Drakkar-Software/Async-Channel&amp;utm_campaign=Badge_Grade)
[![Github-Action-CI](https://github.com/Drakkar-Software/Async-Channel/workflows/Async-Channel-Default-CI/badge.svg)](https://github.com/Drakkar-Software/Async-Channel/actions)
[![Build Status](https://cloud.drone.io/api/badges/Drakkar-Software/Async-Channel/status.svg)](https://cloud.drone.io/Drakkar-Software/Async-Channel)
[![Coverage Status](https://coveralls.io/repos/github/Drakkar-Software/OctoBot-Channels/badge.svg?branch=master)](https://coveralls.io/github/Drakkar-Software/OctoBot-Channels?branch=master)
[![Doc Status](https://readthedocs.org/projects/octobot-channels/badge/?version=stable)](https://octobot-channels.readthedocs.io/en/stable/?badge=stable)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Python multi-task communication library. Used by [OctoBot](https://github.com/Drakkar-Software/OctoBot) project.

## Installation
With python3 : `pip install async-channel`

## Usage
Example
```python
import async_channel.consumer as consumer
import async_channel.producer as producer
import async_channel.channels as channels
import async_channel.util as util

class AwesomeProducer(producer.Producer):
    pass

class AwesomeConsumer(consumer.Consumer):
    pass

class AwesomeChannel(channels.Channel):
    PRODUCER_CLASS = AwesomeProducer
    CONSUMER_CLASS = AwesomeConsumer

async def callback(data):
    print("Consumer called !")
    print("Received : " + data)

# Creates the channel
await util.create_channel_instance(AwesomeChannel, channels.Channels)

# Add a new consumer to the channel
await channels.Channels.get_chan("Awesome").new_consumer(callback)

# Creates a producer that send data to the consumer through the channel
producer = AwesomeProducer(channels.Channels.get_chan("Awesome"))
await producer.run()
await producer.send("test")

# Stops the channel with all its producers and consumers
# await channels.Channels.get_chan("Awesome").stop()
```

# Developer documentation
On [readthedocs.io](https://octobot-channels.readthedocs.io/en/latest/)
