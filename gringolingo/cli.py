from functools import lru_cache
from typing import Any, Dict, List
import openai
import pathlib
import tiktoken

thisdir = pathlib.Path(__file__).parent.absolute()

api_key_path = pathlib.Path.home().joinpath('.gringolingo', 'api_key.txt')
try:
    openai.api_key = api_key_path.read_text().strip()
except FileNotFoundError:
    print("Could not find API key. Please create a file at {}".format(api_key_path))
    exit(1)

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

def main():
    prompt = load_prompt()

    print(f"Prompt Tokens: {get_num_tokens(''.join(prompt))}")


    def new_conversation() -> List[Dict[str, str]]:
        welcome_message = " ".join([
            "Olá, meu nome é Gringo Lingo e eu vou ser seu tutor de inglês!",
            "Vamos conversar e eu vou te corregir seu inglês quando presiar.",
            "Pode fazer qualquer pergunta eu farei o meu melhor para te ajudar!",
            "Se quiser começar de novo, só manda '/reset'.",
        ])

        print(f"Gringo Lingo: {welcome_message}")

        # Get first question
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Start with a conversation starter about a new topic."}
            ]
        )

        first_message = response.choices[0]["message"]
        print(f"Gringo Lingo: {first_message['content'].strip()}")
        return [first_message]

    conversation = new_conversation()
    while True:
        # get user response
        res = input(f"You: ")
        while res == "/reset":
            conversation = new_conversation()
            res = input("You: ")
            
        conversation.append({"role": "user", "content": res})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages = [
                {"role": "system", "content": prompt},
                *trim_conversation(conversation, 1024)
            ]
        )

        message = response.choices[0]["message"]
        conversation.append(message)
        print(f"Gringo Lingo: {message['content'].strip()}")


if __name__ == '__main__':
    main()