import os
import discord
from deep_translator import GoogleTranslator

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Bot online: {client.user}")

@client.event
async def on_message(message):
    # Không xử lý tin nhắn của bot
    if message.author.bot:
        return

    text = message.content.strip()

    if not text:
        return

    try:
        # Tự nhận diện ngôn ngữ và dịch sang tiếng Việt
        translated = GoogleTranslator(
            source="auto",
            target="vi"
        ).translate(text)

        # Nếu kết quả giống hệt tin gốc thì không gửi lại
        if translated and translated.strip() != text:
            await message.reply(
                f"🇻🇳 **Tiếng Việt:**\n{translated}",
                mention_author=False
            )

    except Exception as e:
        print(f"Translation error: {e}")

client.run(TOKEN)
