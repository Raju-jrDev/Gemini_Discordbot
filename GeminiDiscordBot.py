import os
import re

import aiohttp
import discord
import google.generativeai as genai
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive
# keep_alive() should be called after bot.run() to avoid multiple event loops

message_history = {}

load_dotenv()

GOOGLE_AI_KEY = os.getenv("GOOGLE_AI_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MAX_HISTORY = int(os.getenv("MAX_HISTORY"))
ALLOWED_CHANNEL_IDS = list(map(int, os.getenv("ALLOWED_CHANNEL_IDS").split(',')))

#---------------------------------------------System Prompt!-------------------------------------------------

system_prompt = "you are a friendly bot"
image_prompt = "you are a friendly bot"
#---------------------------------------------AI Configuration-------------------------------------------------

# Configure the generative AI model
genai.configure(api_key=GOOGLE_AI_KEY)
text_generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 512,
}
image_generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 512,
}
video_generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 512,
}
audio_generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 512,
}
pdf_generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 512,
}


safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]
text_model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=text_generation_config, safety_settings=safety_settings,system_instruction=system_prompt)
image_model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=image_generation_config, safety_settings=safety_settings,system_instruction=image_prompt)
video_model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=video_generation_config, safety_settings=safety_settings,system_instruction=image_prompt)
audio_model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=audio_generation_config, safety_settings=safety_settings,system_instruction=image_prompt)
pdf_model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=pdf_generation_config, safety_settings=safety_settings,system_instruction=image_prompt)


#---------------------------------------------Discord Code-------------------------------------------------

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', description="Assistant bot", intents=intents)

@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f'Gemini Bot Logged in as {bot.user}')
    print("----------------------------------------")

@bot.event
async def on_disconnect():
    print('Bot disconnected! Attempting to reconnect...')
    try:
        await bot.connect(reconnect=True)
    except Exception as e:
        print(f'Error during reconnection: {e}')

@bot.event
async def on_error(event, *args, **kwargs):
    print(f'An error occurred: {event}')

# Check if the message is in an allowed channel
def is_allowed_channel(ctx):
    return ctx.channel.id in ALLOWED_CHANNEL_IDS

    if not is_allowed_channel(message):
        await message.channel.send("This bot is not allowed to be used in this channel.")
async def on_message(message):
    if not is_allowed_channel(message):
        await message.send("This bot is not allowed to be used in this channel.")
    # Ignore messages sent by the bot
    if message.author == bot.user or message.mention_everyone:
        return

    # Process the message content
    cleaned_text = clean_discord_message(message.content)

    async with message.channel.typing():
        # Check for image attachments
        if message.attachments:
            print("New Image Message FROM:" + str(message.author.id) + ": " + cleaned_text)
            #Currently no chat history for images
            for attachment in message.attachments:
                #these are the only image extentions it currently accepts
                if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                    await message.add_reaction('🎨')

                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as resp:
                            if resp.status != 200:
                                await message.channel.send('Unable to download the image.')
                                return
                            image_data = await resp.read()
                            response_text = await generate_response_with_image_and_text(image_data, cleaned_text)
                            #Split the Message so discord does not get upset
                            await split_and_send_messages(message, response_text, 1700)
                            return
                elif any(attachment.filename.lower().endswith(ext) for ext in ['.mp4', '.mov', '.avi', '.flv', '.wmv', '.webm', '.mkv']):
                    await message.add_reaction('🎥')
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as resp:
                            if resp.status != 200:
                                await message.channel.send('Unable to download the video.')
                                return
                            video_data = await resp.read()
                            response_text = await generate_response_with_video_and_text(video_data, cleaned_text)
                            #Split the Message so discord does not get upset
                            await split_and_send_messages(message, response_text, 1700)
                            return
                elif any(attachment.filename.lower().endswith(ext) for ext in ['.mp3', '.wav', '.flac', '.ogg', '.wma', '.aac', '.m4a']):
                    await message.add_reaction('🎵')
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as resp:
                            if resp.status != 200:
                                await message.channel.send('Unable to download the audio.')
                                return
                            audio_data = await resp.read()
                            response_text = await generate_response_with_audio_and_text(audio_data, cleaned_text)
                            #Split the Message so discord does not get upset
                            await split_and_send_messages(message, response_text, 1700)
                            return
                elif any(attachment.filename.lower().endswith(ext) for ext in ['.pdf']):
                    await message.add_reaction('📄')
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as resp:
                            if resp.status != 200:
                                await message.channel.send('Unable to download the pdf.')
                                return
                            pdf_data = await resp.read()
                            response_text = await generate_response_with_pdf_and_text(pdf_data, cleaned_text)
                            #Split the Message so discord does not get upset
                            await split_and_send_messages(message, response_text, 1700)
                            return
        #Not an Image/video/audio do text response
        else:
            print("New Message FROM:" + str(message.author.id) + ": " + cleaned_text)
            #Check for Keyword Reset
            if "RESET" in cleaned_text:
                #End back message
                if message.author.id in message_history:
                    del message_history[message.author.id]
                await message.channel.send("🤖 History Reset for user: " + str(message.author.name))
                return
            await message.add_reaction('💬')

            #Check if history is disabled just send response
            if(MAX_HISTORY == 0):
                response_text = await generate_response_with_text(cleaned_text)
                #add AI response to history
                await split_and_send_messages(message, response_text, 1700)
                return;
            #Add users question to history
            update_message_history(message.author.id,cleaned_text)
            response_text = await generate_response_with_text(get_formatted_message_history(message.author.id))
            #add AI response to history
            update_message_history(message.author.id,response_text)
            #Split the Message so discord does not get upset
            await split_and_send_messages(message, response_text, 1700)

#---------------------------------------------AI Generation History-------------------------------------------------

async def generate_response_with_text(message_text):
    prompt_parts = [message_text]
    print("Got textPrompt: " + message_text)
    response = text_model.generate_content(prompt_parts)
    if(response._error):
        return "❌" +  str(response._error)
    return response.text

async def generate_response_with_image_and_text(image_data, text):
    image_parts = [{"mime_type": "image/jpeg", "data": image_data}]
    prompt_parts = [image_parts[0], f"\n{text if text else 'What is this a picture of?'}"]
    response = image_model.generate_content(prompt_parts)
    if(response._error):
        return "❌" +  str(response._error)
    return response.text

async def generate_response_with_video_and_text(video_data, text):
    video_parts = [{"mime_type": "video/mp4", "data": video_data}]
    prompt_parts = [video_parts[0], f"\n{text if text else 'What is this a video of?'}"]
    response = image_model.generate_content(prompt_parts)
    if(response._error):
        return "❌" +  str(response._error)
    return response.text

async def generate_response_with_audio_and_text(audio_data, text):
    audio_parts = [{"mime_type": "audio/mp3", "data": audio_data}]
    prompt_parts = [audio_parts[0], f"\n{text if text else 'What is this a audio of?'}"]
    response = image_model.generate_content(prompt_parts)
    if(response._error):
        return "❌" +  str(response._error)
    return response.text

async def generate_response_with_pdf_and_text(pdf_data, text):
    pdf_parts = [{"mime_type": "application/pdf", "data": pdf_data}]
    prompt_parts = [pdf_parts[0], f"\n{text if text else 'What is this a pdf of?'}"]
    response = image_model.generate_content(prompt_parts)
    if(response._error):
        return "❌" +  str(response._error)
    return response.text

#---------------------------------------------Message History-------------------------------------------------
def update_message_history(user_id, text):
    # Check if user_id already exists in the dictionary
    if user_id in message_history:
        # Append the new message to the user's message list
        message_history[user_id].append(text)
        # If there are more than 12 messages, remove the oldest one
        if len(message_history[user_id]) > MAX_HISTORY:
            message_history[user_id].pop(0)
    else:
        # If the user_id does not exist, create a new entry with the message
        message_history[user_id] = [text]

def get_formatted_message_history(user_id):
    """
    Function to return the message history for a given user_id with two line breaks between each message.
    """
    if user_id in message_history:
        # Join the messages with two line breaks
        return '\n\n'.join(message_history[user_id])
    else:
        return "No messages found for this user."

#---------------------------------------------Sending Messages-------------------------------------------------
async def split_and_send_messages(message_system, text, max_length):

    # Split the string into parts
    messages = []
    for i in range(0, len(text), max_length):
        sub_message = text[i:i+max_length]
        messages.append(sub_message)

    # Send each part as a separate message
    for string in messages:
        await message_system.channel.send(string)

def clean_discord_message(input_string):
    # Create a regular expression pattern to match text between < and >
    bracket_pattern = re.compile(r'<[^>]+>')
    # Replace text between brackets with an empty string
    cleaned_content = bracket_pattern.sub('', input_string)
try:
    bot.run(DISCORD_BOT_TOKEN)
except Exception as e:
    print(f'Error running the bot: {e}')
finally:
    keep_alive()

#---------------------------------------------Run Bot-------------------------------------------------
bot.run(DISCORD_BOT_TOKEN)