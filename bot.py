import logging
import os
import random
from typing import Dict, List
import openai
import pathlib
import tiktoken
from topics import TOPICS

thisdir = pathlib.Path(__file__).resolve().parent
# get from .env file if it exists
if thisdir.joinpath('.env').exists():
    from dotenv import load_dotenv
    load_dotenv()

if "OPENAI_API_KEY" in os.environ:
    openai.api_key = os.environ["OPENAI_API_KEY"]

# if no API KEY, raise error
if not openai.api_key:
    raise ValueError("No OpenAI API Key found. Please set the OPENAI_API_KEY environment variable.")

# enumeration for supported languages
class LanguageBot:
    def __init__(self, 
                 target_language: str, 
                 source_language: str, 
                 difficulty: str,
                 welcome_message: str) -> None:
        self.target_language = target_language 
        self.source_language = source_language
        self.difficulty = difficulty
        self.welcome_message = welcome_message

    def get_starter(self, include_welcome_message: bool = True) -> str:
        topic = random.choice(TOPICS)

        CONVERSATION_STARTER_PROMPT = " ".join([
            f"Generate a conversation starter in {self.difficulty}-level {self.target_language} about {topic}.",
            f"Do not wrap in quotation marks or include context.",
            f"Only respond with the conversation starter."
        ])
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages = [
                {"role": "system", "content": CONVERSATION_STARTER_PROMPT}
            ]
        )
        starter = response.choices[0]["message"]["content"]
        if include_welcome_message:
            return f"{self.welcome_message}\n{starter}"
        else:
            return starter
        
    def get_response(self, messages: List[Dict[str, str]]):
        """Get response from openai
        
        Args:
            messages (List[Dict[str, str]]): List of messages. Each message is a dictionary
                with keys "role" and "content". "role" can be "user" or "assistant".
        """
        all_messages = [
            {
                "role": "system", 
                "content": " ".join([
                    f"You are a {self.target_language} language tutor for a {self.source_language} speaker.",
                    f"If there are English mistakes in the user messages, you *must* correct it.",
                    f"Then continue the conversation using {self.difficulty}-level {self.target_language}.",
                    f"If there are no English mistakes, just continue the conversation.\n\n",
                ])
            },
            *messages,
            {
                "role": "system", 
                "content": " ".join([
                    f"If there are any {self.target_language} mistakes in the user's response, you *must* correct them, then continue the conversation using {self.difficulty}-level {self.target_language}.",
                    f"If there are no {self.target_language} mistakes, just continue the conversation.\n\n",
                ])
            }
        ]
        logging.info(f"all_messages: {all_messages}")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=all_messages
        )

        bot_message = response.choices[0]["message"]
        return bot_message["content"]

def get_num_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding('gpt2')
    num_tokens = len(encoding.encode(text))
    return num_tokens

def trim_conversation(conversation: List[Dict[str, str]], max_tokens: int) -> List[str]:
    """Trims a conversation to a maximum number of tokens. Keeping the most recent messages."""
    num_tokens = 0
    return_conversation = []
    for message in conversation[::-1]:
        num_tokens += get_num_tokens(message["content"])
        return_conversation.append(message)
        if num_tokens >= max_tokens:
            break
    return return_conversation[::-1]