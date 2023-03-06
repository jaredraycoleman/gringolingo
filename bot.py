from datetime import datetime
from functools import lru_cache
import os
import random
from typing import Any, Dict, List
import openai
import pathlib
import tiktoken
from topics import TOPICS

from db import Message, MessageType

thisdir = pathlib.Path(__file__).resolve().parent
openai.api_key = os.environ["OPENAI_API_KEY"]

# enumeration for supported languages

LEARNING_MODE = "English"

STARTER_PROMPT = " ".join([
    f"Be my {LEARNING_MODE} Tutor.", 
    f"Converse with me in {LEARNING_MODE} and correct my {LEARNING_MODE} when I make mistakes."
])

WELCOME_MESSAGES = {
    "English": " ".join([
        f"Olá, meu nome é Gringo Lingo e eu serei seu tutor de inglês!",
        f"Vamos conversar e eu vou corrigir seu inglês quando necessário.",
        f"Você pode fazer qualquer pergunta e eu farei o meu melhor para ajudá-lo!",
        f"Se quiser começar de novo, basta digitar '/reset'."
    ]),
    "Portuguese": " ".join([
        f"Hello, my name is Gringo Lingo and I will be your Portuguese tutor!",
        f"Let's talk and I will correct your Portuguese when needed.", 
        f"You can ask me any questions and I will do my best to help you!", 
        f"If you want to start over, just type '/reset'."
    ])
}

def get_starter() -> str:
    topic = random.choice(TOPICS)

    CONVERSATION_STARTER_PROMPT = " ".join([
        f"Generate a conversation starter in {LEARNING_MODE} about {topic}.",
        f"Don't include quotation marks or context, only respond with the conversation starter."
    ])
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = [
            {"role": "system", "content": CONVERSATION_STARTER_PROMPT}
        ]
    )
    starter = response.choices[0]["message"]["content"]
    return f"{WELCOME_MESSAGES[LEARNING_MODE]}\n{starter}"

@lru_cache(maxsize=None)
def load_prompt() -> str:
    return thisdir.joinpath('prompt.txt').read_text()

def get_num_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding('gpt2')
    num_tokens = len(encoding.encode(text))
    return num_tokens

def trim_conversation(conversation: List[Dict[str, str]], max_tokens: int) -> List[str]:
    """Trims a conversation to a maximum number of tokens. Keeping the most recent messages."""
    encoding = tiktoken.get_encoding('gpt2')
    num_tokens = 0
    return_conversation = []
    for message in conversation[::-1]:
        num_tokens += get_num_tokens(message["content"])
        return_conversation.append(message)
        if num_tokens >= max_tokens:
            break
    return return_conversation[::-1]

def get_response(phone_id: str, new_message: str):
    messages = Message.get_last_n_messages(phone_id, 100)

    print("Last 100 messages:", " --- ".join([m.content for m in messages]), "\n")

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

    openai_messages = openai_messages[::-1]

    # Add new_message to database
    if new_message.startswith("/reset") or len(openai_messages) == 0:
        Message.add_message(phone_id, new_message, MessageType.bot_command_message, timestamp=datetime.now())
        starter = get_starter()
        Message.add_message(phone_id, starter, MessageType.bot_message, timestamp=datetime.now())        
        return starter
    
    Message.add_message(phone_id, new_message, MessageType.user_message, timestamp=datetime.now())

    reminder = f"(Remember to correct my mistakes if I made any, then continue the conversation using beginners {LEARNING_MODE})"
    openai_messages.append({"role": "user", "content": f"{new_message}\n\n{reminder}"})

    print(trim_conversation(openai_messages, 3000))
    # get response from openai
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = [
            {"role": "system", "content": STARTER_PROMPT},
            *trim_conversation(openai_messages, 3000)
        ]
    )

    # Add response to database
    bot_message = response.choices[0]["message"]
    Message.add_message(phone_id, bot_message["content"], MessageType.bot_message, timestamp=datetime.now())

    return bot_message["content"]

def cli():
    # don't print sqlalchemy logs

    phone_id = "123456789"
    user_message = "/reset"
    while True:
        print("My message:", user_message)
        bot_message = get_response(phone_id, user_message)
        print("GringoLingo:", bot_message) 
        user_message = input("You: ")

if __name__ == "__main__":
    cli()


