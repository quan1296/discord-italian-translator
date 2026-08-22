import os
import discord
from deep_translator import GoogleTranslator
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID"))

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


def detect_language(text):
    try:
        return detect(text)
    except:
        return None


def translate(text, target):
    return GoogleTranslator(
        source="auto",
        target=target
    ).translate(text)


@client.event
async def on_ready():
    print(f"✅ Bot online: {client.user}")


@client.event
async def on_message(message):

    # Không xử lý tin nhắn từ bot
    if message.author.bot:
        return

    text = message.content.strip()

    if not text:
        return

    language = detect_language(text)

    # =====================================
    # BẠN NHẮN TIẾNG VIỆT
    # -> DỊCH SANG Ý CÔNG KHAI
    # =====================================

    if message.author.id == OWNER_USER_ID and language == "vi":

        try:
            translated = translate(text, "it")

            await message.reply(
                f"🇮🇹 **Italiano:**\n{translated}",
                mention_author=False
            )

        except Exception as e:
            print("Lỗi Việt → Ý:", e)

        return


    # =====================================
    # NGƯỜI KHÁC NHẮN TIẾNG Ý
    # -> DM RIÊNG CHO BẠN
    # =====================================

    if message.author.id != OWNER_USER_ID and language == "it":

        try:
            translated = translate(text, "vi")

            owner = await client.fetch_user(OWNER_USER_ID)

            await owner.send(
                f"🇻🇳 **{message.author.display_name}:**\n"
                f"{translated}\n\n"
                f"💬 Tin gốc: {text}"
            )

        except Exception as e:
            print("Lỗi Ý → Việt DM:", e)


client.run(TOKEN)
