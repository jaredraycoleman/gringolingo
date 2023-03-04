from datetime import datetime
from functools import lru_cache
import os
import random
from typing import Any, Dict, List
import openai
import pathlib
import tiktoken
from topics import TOPICS

from db import User, Message, MessageType


thisdir = pathlib.Path(__file__).resolve().parent
openai.api_key = os.environ["OPENAI_API_KEY"]

STARTER_PROMPT = "Be my English Tutor. Converse with me and correct my English when I make mistakes."
WELCOME_MESSAGE = " ".join([
    "Olá, meu nome é Gringo Lingo e eu vou ser seu tutor de inglês!",
    "Vamos conversar e eu vou te corregir seu inglês quando presiar.",
    "Pode fazer qualquer pergunta eu farei o meu melhor para te ajudar!",
    "Se quiser começar de novo, só manda '/reset'.",
])

def get_starter() -> str:
    topic = random.choice(TOPICS)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = [
            {"role": "system", "content": STARTER_PROMPT},
            {"role": "system", "content": f"Start with a conversation starter about {topic}."}
        ]
    )
    starter = response.choices[0]["message"]["content"]
    return f"{WELCOME_MESSAGE}\n\n{starter}"

@lru_cache(maxsize=None)
def load_prompt() -> str:
    return thisdir.joinpath('prompt.txt').read_text()

def get_num_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding('gpt2')
    num_tokens = len(encoding.encode(text))
    return num_tokens

def trim_conversation(conversation: List[Dict[str, str]], max_tokens: int) -> List[str]:
    encoding = tiktoken.get_encoding('gpt2')
    tokens = 0
    for i, message in enumerate(conversation[::-1]):
        tokens += len(encoding.encode(message["content"]))
        if tokens > max_tokens:
            return conversation[-i:]
    return conversation


def get_response(phone_id: str, new_message: str):
    messages = Message.get_last_n_messages(phone_id, 100)

    # format messages for openai
    openai_messages = []
    for message in messages[::-1]:
        if message.message_type == MessageType.user_message:
            openai_messages.append({"role": "user", "content": message.content})
        elif message.message_type == MessageType.system:
            openai_messages.append({"role": "system", "content": message.content})
        elif message.message_type == MessageType.bot_message:
            openai_messages.append({"role": "assistant", "content": message.content})
        elif message.message_type == MessageType.bot_command_message:
            if message.content == "/reset":
                break

    # Add new_message to database
    if new_message.startswith("/reset") or len(openai_messages) == 0:
        Message.add_message(phone_id, new_message, MessageType.bot_command_message, timestamp=datetime.now())
        starter = get_starter()
        Message.add_message(phone_id, starter, MessageType.bot_message, timestamp=datetime.now())        
        return starter
    

    Message.add_message(phone_id, new_message, MessageType.user_message, timestamp=datetime.now())

    reminder = "(Remember to correct my mistakes if I made any, then continue the conversation using beginners english)"
    openai_messages.append({"role": "user", "content": f"{new_message}\n\n{reminder}"})

    # get response from openai
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = [
            {"role": "system", "content": STARTER_PROMPT},
            *trim_conversation(openai_messages, 1024)
        ]
    )

    # Add response to database
    bot_message = response.choices[0]["message"]
    Message.add_message(phone_id, bot_message["content"], MessageType.bot_message, timestamp=datetime.now())

    return bot_message["content"]

def cli():
    # don't print sqlalchemy logs
    import logging
    logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

    phone_id = "123456789"
    reply = "/reset"
    while True:
        response = get_response(phone_id, reply)
        print("GringoLingo:", response) 
        reply = input("You: ")

if __name__ == "__main__":
    cli()


