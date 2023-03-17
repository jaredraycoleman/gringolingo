from datetime import datetime
import logging
from typing import List
import discord
from discord.ext import commands
from discord.message import Message
from bot import LanguageBot

from dotenv import load_dotenv
import pathlib
import os
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
thisdir = pathlib.Path(__file__).resolve().parent
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)


USER_STATE = {}

class NoTargetLanguageError(Exception):
    MESSAGE = "\n".join([
        "Please specify the langauge you want to learn by sending either !portuguese or !english.",
        "Especifique o idioma que deseja aprender enviando !portuguese ou !english.",
        "",
        "Send !help to see all available commands.",
        "Mande !help para ver todos os comandos disponíveis",
    ])

difficulties = {
    "easy": "beginner",
    "medium": "intermediate",
    "hard": "advanced" 
}

class DiscordLanguageBot(LanguageBot):
    def __init__(self, user: str) -> None:
        try:
            USER_STATE.setdefault(user, {})
            target_language = USER_STATE[user]["mode"].lower().strip()
            source_language = "english" if target_language == "portuguese" else "portuguese"
        except KeyError as e:
            raise NoTargetLanguageError(f"User {user} has not set a language learning mode.")
        
        difficulty = USER_STATE[user].get("difficulty", "easy")
        bot_difficulty = difficulties[difficulty]
        # translate difficulty to portuguese
        port_difficulty = {
            "beginner": "iniciante",
            "intermediate": "intermediário",
            "advanced": "avançado"
        }[bot_difficulty]
        
        if target_language == "english":
            welcome_message = " ".join([
                f"Olá, meu nome é Gringo Lingo e eu serei seu tutor de inglês!",
                f"Vamos conversar e eu vou corrigir seu inglês quando necessário.",
                f"Você pode fazer qualquer pergunta e eu farei o meu melhor para ajudá-lo!",
                f"Se você quiser que eu inicie uma nova conversa, basta digitar '!new'.",
                f"Se quiser começar de novo, basta digitar '!reset'.",
                f"Neste momento, estou configurado para usar inglês **{port_difficulty}**",
                f"Se quiser alterar a dificuldade, basta digitar '!easy' (fácil), '!medium' (médio) ou '!hard' (difícil)."
            ])
        else:
            welcome_message = " ".join([
                f"Hello, my name is Gringo Lingo and I will be your Portuguese tutor!",
                f"Let's chat and I will correct your Portuguese when necessary.",
                f"You can ask any questions and I will do my best to help you!",
                f"If you want me to start a new conversation, just type '!new'.",
                f"If you want to start over, just type '!reset'.",
                f"Right now, I'm set to use **{bot_difficulty}** Portuguese",
                f"If you want to change the difficulty, just type '!easy' (beginner), '!medium' (intermediate), or '!hard' (advanced)."
            ])
        super().__init__(
            target_language=target_language,
            source_language=source_language,
            difficulty=bot_difficulty,
            welcome_message=welcome_message
        )

    def get_response(self, messages: List[Message]) -> str:
        messages = [
            {
                "role": "assistant" if message.author == bot.user else "user", 
                "content": f"{message.content.strip()}\n\n"}
            for message in messages
        ]
        logging.info(f"Messages: {messages}")
        return super().get_response(messages) 

@bot.event
async def on_ready():
    print(f'{bot.user} is online!')

@bot.command(name="new")
async def new(ctx: commands.Context):
    """Creates a new conversation starter"""
    try:
        discord_bot = DiscordLanguageBot(ctx.author.name)
        await ctx.send(discord_bot.get_starter(include_welcome_message=False))
    except NoTargetLanguageError as e:
        await ctx.send(NoTargetLanguageError.MESSAGE)

@bot.command(name="reset")
async def reset(ctx: commands.Context):
    """Resets the conversation (not user data) so previous messages are not used"""
    try:
        discord_bot = DiscordLanguageBot(ctx.author.name)
        # set reset timestampt to ctx.message.created_at
        USER_STATE.setdefault(ctx.author.name, {})
        USER_STATE[ctx.author.name]["reset_timestamp"] = ctx.message.created_at
        await ctx.send(discord_bot.welcome_message)
    except NoTargetLanguageError as e:
        await ctx.send(NoTargetLanguageError.MESSAGE)
    
@bot.command(name="portuguese")
async def language(ctx):
    """Set language learning mode to portuguese."""
    logging.info(f"Setting language to portuguese for {ctx.author.name}")
    
    USER_STATE.setdefault(ctx.author.name, {})
    USER_STATE[ctx.author.name]["mode"] = "portuguese"
    await reset(ctx)

@bot.command(name="english")
async def language(ctx):
    """Set language learning mode to english."""
    logging.info(f"Setting language to english for {ctx.author.name}")
    
    USER_STATE.setdefault(ctx.author.name, {})
    USER_STATE[ctx.author.name]["mode"] = "english"
    await reset(ctx)

@bot.command(name="status")
async def status(ctx):
    """Get current language learning mode."""
    logging.info(f"Getting status")
    
    USER_STATE.setdefault(ctx.author.name, {})
    await ctx.send(f"Current language learning mode: {USER_STATE[ctx.author.name].get('mode', 'None')}")
    await ctx.send(f"Current difficulty: {USER_STATE[ctx.author.name].get('difficulty', 'easy')}")

@bot.command(name="easy")
async def easy(ctx):
    """Set difficulty to easy."""
    logging.info(f"Setting difficulty to easy for {ctx.author.name}")
    
    USER_STATE.setdefault(ctx.author.name, {})
    USER_STATE[ctx.author.name]["difficulty"] = "easy"
    await reset(ctx)

@bot.command(name="medium")
async def medium(ctx):
    """Set difficulty to medium."""
    logging.info(f"Setting difficulty to medium for {ctx.author.name}")
    
    USER_STATE.setdefault(ctx.author.name, {})
    USER_STATE[ctx.author.name]["difficulty"] = "medium"
    await reset(ctx)

@bot.command(name="hard")
async def hard(ctx):
    """Set difficulty to hard."""
    logging.info(f"Setting difficulty to hard for {ctx.author.name}")
    
    USER_STATE.setdefault(ctx.author.name, {})
    USER_STATE[ctx.author.name]["difficulty"] = "hard"
    await reset(ctx)


@bot.command(name="help")
async def help_command(ctx):
    help_str = "\n".join([
        "Commands/Commandos:",
        "  !new         Start a new conversation",
        "               Iniciar uma nova conversa",
        "  !reset       Reset the conversation",
        "               Resetar a conversa",
        "  !portuguese  Set language learning mode to portuguese",
        "               Definir o modo de aprendizado para português",
        "  !english     Set language learning mode to english",
        "               Definir o modo de aprendizado para inglês",
        "  !status      Get current language learning mode",
        "               Ver o modo de aprendizado atual",
        "  !help        Show this help message",
        "               Mostrar esta mensagem de ajuda",
    ])

    # put in code block
    help_str = "```\n" + help_str + "\n```"
    await ctx.send(help_str)


@bot.event
async def on_message(message: Message):
    if message.author == bot.user:
        return # ignore bot messages
    
    # only work on DM channels or if mentioned
    on_private = message.channel.type == discord.ChannelType.private
    on_mention = bot.user.mentioned_in(message)
    logging.info(f"on_private: {on_private}, on_mention: {on_mention}")
    if not on_private and not on_mention:
        return
    
    # strip mention from message
    if on_mention:
        message.content = message.content.replace(f"<@{bot.user.id}>", "").strip()
    
    # if is command, don't ask for response
    if not message.content.startswith('!'):
        channel = message.channel

        logging.info(f"Received message: {message.content} from {message.author} in {channel}")

        # Get the last 20 messages in the channel for context
        reset_time = USER_STATE.get(message.author.name, {}).get("reset_timestamp")
        messages = [msg async for msg in channel.history(limit=20, after=reset_time)]
        # messages = list(reversed(messages))

        try:
            discord_bot = DiscordLanguageBot(message.author.name)
            response = discord_bot.get_response(messages)
            await channel.send(response)
        except NoTargetLanguageError as e:
            await channel.send(NoTargetLanguageError.MESSAGE)

    # Process commands after logging messages
    await bot.process_commands(message)

# reload automatically when code changes
bot.run(BOT_TOKEN)
