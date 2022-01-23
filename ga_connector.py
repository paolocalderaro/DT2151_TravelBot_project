import logging
import json
from sanic import Blueprint, response
from sanic.request import Request
from typing import Text, Optional, List, Dict, Any

from rasa.core.channels.channel import UserMessage, OutputChannel
from rasa.core.channels.channel import InputChannel
from rasa.core.channels.channel import CollectingOutputChannel
from datetime import datetime


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.FileHandler(filename=".//logs//google_connector.log", mode="a")
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch)
logger.debug(f"START NEW SESSION. DATE: {datetime.now()}")

class GoogleConnector(InputChannel):
    """A custom http input channel.

    This implementation is the basis for a custom implementation of a chat
    frontend. You can customize this to send messages to Rasa Core and
    retrieve responses from the agent."""

    @classmethod
    def name(cls):
        return "google_assistant"

    def blueprint(self, on_new_message):

        google_webhook = Blueprint('google_webhook', __name__)

        @google_webhook.route("/", methods=['GET'])
        async def health(request):
            return response.json({"status": "ok", "my_name_is": "google_webhook"})

        @google_webhook.route("/webhook", methods=['POST'])
        async def receive(request):
            payload = request.json
            intent = payload['inputs'][0]['intent']
            text = payload['inputs'][0]['rawInputs'][0]['query']
            image = None
            message = None
            fp = None
            # sender_id is necessary in order to start different flows for different conversation.
            # otherwise, it would be a mess. The system wouldn't be able to distinguish messages from different users
            # and it will make wrong intent predictions
            sender_id = payload['conversation']['conversationId'].replace("_","").replace("-","")
            try:
                fp = open(f".//logs//conversation_{sender_id}.log", "a+")
                logger.debug(f"payload: {payload}")
                logger.debug(f"intent: {intent}")
                logger.debug(f"text: {text}")
                fp.writelines(f"USER: {text} \n")
            except:
                pass
            if intent == 'actions.intent.MAIN':
                message = "Hello! Welcome to the Rasa-powered Google Assistant skill. You can start by saying hi."
            else:
                message = "An internal error occurred. I'm sorry for the inconvenient"
                try:
                    out = CollectingOutputChannel()
                    await on_new_message(UserMessage(text, out, sender_id=sender_id))
                    try:
                        for m in out.messages:
                            logger.debug("Message {}".format(m))
                    except Exception as e:
                        logger.error(f"Exception occurred during logging: {e}")
                    responses = [m["text"] if 'text' in m.keys() else None for m in out.messages]
                    images = [m['image'] if 'image' in m.keys() else None for m in out.messages]
                    responses = list(filter(lambda x: x is not None, responses))
                    images = list(filter(lambda x: x is not None, images))
                    message = responses[0] if len(responses) > 0 else "No response was found"
                    message = message.encode("ascii", "ignore")
                    image = images[0] if len(images) > 0 else None
                    try:
                        logger.debug(f"message: {message}")
                        logger.debug(f"responses: {responses}")
                        logger.debug(f"image: {image}")
                        if fp is not None:
                            fp.writelines(f"BOT: {message}\n")
                    except:
                        pass
                except Exception as e:
                    logger.error(f"Exception occured in ga_connector: {e}")
            if image is not None:
                r = {
                    "expectUserResponse": 'true',
                    "expectedInputs": [
                        {
                            "possibleIntents": [
                                {
                                    "intent": "actions.intent.TEXT"
                                }
                            ],
                            "inputPrompt": {
                                "richInitialPrompt": {
                                    "items": [
                                        {
                                            "simpleResponse": {
                                                "textToSpeech": message,
                                                "displayText": message
                                            }
                                        },
                                        {
                                            "basicCard": {
                                                "title": "Point of Interest",
                                                "subtitle": message,
                                                "formattedText": "Image",
                                                "image": {
                                                    "url": image,
                                                    "accessibilityText": "Point of Interest"
                                                },
                                                "imageDisplayOptions": "CROPPED"
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                }
            else:
                r = {
                    "expectUserResponse": 'true',
                    "expectedInputs": [
                        {
                            "possibleIntents": [
                                {
                                    "intent": "actions.intent.TEXT"
                                }
                            ],
                            "inputPrompt": {
                                "richInitialPrompt": {
                                    "items": [
                                        {
                                            "simpleResponse": {
                                                "textToSpeech": message,
                                                "displayText": message
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                }
            fp.close()
            return response.json(r)

        return google_webhook
