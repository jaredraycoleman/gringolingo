import logging
import pathlib
import openai

import requests
from heyoo import WhatsApp
from os import environ
from flask import Flask, request, make_response
from bot import STARTER_PROMPT, get_response, get_starter, trim_conversation

# load from .env file if it exists
if pathlib.Path(".env").exists():
    from dotenv import load_dotenv

    load_dotenv()

messenger = WhatsApp(environ.get("TOKEN"), phone_number_id=environ.get("PHONE_NUMBER_ID")) #this should be writen as 
#WhatsApp(token = "inpust accesstoken", phone_number_id="input phone number id") #messages are not recieved without this pattern

# Here's an article on how to get the application secret from Facebook developers portal.
# https://support.appmachine.com/support/solutions/articles/80000978442
VERIFY_TOKEN = environ.get("APP_SECRET") #application secret here
MESSENGER_API_KEY = environ.get("MESSENGER_API_KEY") #messenger api key here
MESSENGER_PAGE_ID = "109100192122534" # environ.get("MESSENGER_PAGE_ID") #messenger page id here

#to be tested in prod environment
# messenger = WhatsApp(os.getenv("heroku whatsapp token"),phone_number_id='105582068896304')
# VERIFY_TOKEN = "heroku whatsapp token"

MESSENGER_VERIFY_TOKEN = "strawberry ice cream"

# Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)



@app.route('/')
def index():
    return "Hello, It Works"


@app.route("/messenger", methods=["GET", "POST"])
def messenger_hook():
    # hook for facebook messenger
    if request.method == "GET":
        if request.args.get("hub.verify_token") == MESSENGER_VERIFY_TOKEN:
            logging.info("Verified webhook")
            response = make_response(request.args.get("hub.challenge"), 200)
            response.mimetype = "text/plain"
            return response
        logging.error("Webhook Verification failed")
        return "Invalid verification token"
    
    # Handle Webhook Subscriptions
    data = request.get_json()
    logging.info("Received webhook data: %s", data)

    # get most recent message
    user_messages = sorted(
        [message for message in data["entry"][0]["messaging"] if "message" in message],
        key=lambda message: message["timestamp"],
    )
    try:
        user_message = user_messages[-1]["message"]
    except IndexError:
        logging.error("Messenger: No message found")
        return "ok"

    user_id = user_message["from"]["id"]
    if user_id == MESSENGER_PAGE_ID:
        # ignore messages from the page itself
        logging.info("Messenger: Ignoring message from page")
        return "ok"

    # get chat history
    res = requests.get(
        f"https://graph.facebook.com/v16.0/{MESSENGER_PAGE_ID}", 
        params={
            "access_token": MESSENGER_API_KEY,
            "fields": "conversations{participants,id,messages{message,from}}",
            "user_id": user_id
        }
    )

    logging.info(f"Made request to {res.url}")
    chat_history = res.json()
    # logging.info("Messenger: Chat history: %s", chat_history)

    try:
        conversation = chat_history["conversations"]["data"][0]
    except IndexError:
        logging.error("Messenger: No conversation found")
        return "ok"
    
    openai_messages = []
    num_bot_responses = 0
    for message in conversation["messages"]["data"][::-1]:
        if "message" in message:
            if message["message"] == "/reset":
                break
            role = "user" if message["from"]["id"] == user_id else "assistant"
            openai_messages.insert(0, {"role": role, "content": message["message"]})
            if role == "assistant":
                num_bot_responses += 1

    logging.info("Messenger: OpenAI messages: %s", openai_messages)
    if num_bot_responses == 0:
        bot_message = get_starter()
    else:
        # get response from openai
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages = [
                {"role": "system", "content": STARTER_PROMPT},
                *trim_conversation(openai_messages, 3000)
            ]
        )
        bot_message = response.choices[0]["message"]["content"]

    # send message to facebook
    res = requests.post(
        f"https://graph.facebook.com/v16.0/{MESSENGER_PAGE_ID}/messages",
        params={
            "access_token": MESSENGER_API_KEY
        },
        json={
            "recipient": {"id": sender_id},
            "message": {"text": bot_message}
        }
    )

    return "ok"

@app.route("/whatsapi", methods=["GET", "POST"])
def hook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            logging.info("Verified webhook")
            response = make_response(request.args.get("hub.challenge"), 200)
            response.mimetype = "text/plain"
            return response
        logging.error("Webhook Verification failed")
        return "Invalid verification token"

    # Handle Webhook Subscriptions
    data = request.get_json()
    logging.info("Received webhook data: %s", data)
    changed_field = messenger.changed_field(data)
    if changed_field == "messages":
        new_message = messenger.get_mobile(data)
        if new_message:
            mobile = messenger.get_mobile(data)
            name = messenger.get_name(data)
            message_type = messenger.get_message_type(data)
            logging.info(
                f"New Message; sender:{mobile} name:{name} type:{message_type}"
            )

            messenger.mark_as_read(messenger.get_message_id(data))
            if message_type == "text":
                message = messenger.get_message(data)
                name = messenger.get_name(data)
                logging.info("Message: %s", message)
                response = get_response(mobile, message)
                messenger.send_message(response, mobile)

            elif message_type == "interactive":
                message_response = messenger.get_interactive_response(data)
                intractive_type = message_response.get("type")
                message_id = message_response[intractive_type]["id"]
                message_text = message_response[intractive_type]["title"]
                logging.info(f"Interactive Message; {message_id}: {message_text}")

            elif message_type == "location":
                message_location = messenger.get_location(data)
                message_latitude = message_location["latitude"]
                message_longitude = message_location["longitude"]
                logging.info("Location: %s, %s", message_latitude, message_longitude)

            elif message_type == "image":
                image = messenger.get_image(data)
                image_id, mime_type = image["id"], image["mime_type"]
                image_url = messenger.query_media_url(image_id)
                image_filename = messenger.download_media(image_url, mime_type)
                print(f"{mobile} sent image {image_filename}")
                logging.info(f"{mobile} sent image {image_filename}")

            elif message_type == "video":
                video = messenger.get_video(data)
                video_id, mime_type = video["id"], video["mime_type"]
                video_url = messenger.query_media_url(video_id)
                video_filename = messenger.download_media(video_url, mime_type)
                print(f"{mobile} sent video {video_filename}")
                logging.info(f"{mobile} sent video {video_filename}")

            elif message_type == "audio":
                audio = messenger.get_audio(data)
                audio_id, mime_type = audio["id"], audio["mime_type"]
                audio_url = messenger.query_media_url(audio_id)
                audio_filename = messenger.download_media(audio_url, mime_type)
                print(f"{mobile} sent audio {audio_filename}")
                logging.info(f"{mobile} sent audio {audio_filename}")

            elif message_type == "document":
                file = messenger.get_document(data)
                file_id, mime_type = file["id"], file["mime_type"]
                file_url = messenger.query_media_url(file_id)
                file_filename = messenger.download_media(file_url, mime_type)
                print(f"{mobile} sent file {file_filename}")
                logging.info(f"{mobile} sent file {file_filename}")
            else:
                print(f"{mobile} sent {message_type} ")
                print(data)
        else:
            delivery = messenger.get_delivery(data)
            if delivery:
                print(f"Message : {delivery}")
            else:
                print("No new message")
    return "ok"


if __name__ == '__main__': 
    app.run(debug=True)
