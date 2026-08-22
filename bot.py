import os
import discord
from discord import app_commands
from deep_translator import GoogleTranslator
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID"))

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


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


# =====================================
# KHI BOT ONLINE
# =====================================

@client.event
async def on_ready():
    try:
        await tree.sync()
        print("✅ Đã đồng bộ lệnh /dichcu")
    except Exception as e:
        print("Lỗi đồng bộ lệnh:", e)

    print(f"✅ Bot online: {client.user}")


# =====================================
# CHỨC NĂNG MỚI
# /dichcu + SỐ LƯỢNG 1-100
# =====================================

@tree.command(
    name="dichcu",
    description="Dịch các tin nhắn cũ gần nhất sang tiếng Việt"
)
@app_commands.describe(
    so_luong="Số tin nhắn muốn kiểm tra và dịch (tối đa 100)"
)
async def dichcu(
    interaction: discord.Interaction,
    so_luong: app_commands.Range[int, 1, 100]
):

    # Chỉ bạn mới được sử dụng lệnh này
    if interaction.user.id != OWNER_USER_ID:
        await interaction.response.send_message(
            "❌ Bạn không có quyền sử dụng lệnh này.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        messages = []

        # Lấy số tin nhắn gần nhất trong chính kênh đang dùng lệnh
        async for msg in interaction.channel.history(
            limit=so_luong,
            oldest_first=True
        ):
            messages.append(msg)

        translated_messages = []

        for msg in messages:

            # Bỏ qua bot
            if msg.author.bot:
                continue

            # Bỏ qua tin nhắn của chính bạn
            if msg.author.id == OWNER_USER_ID:
                continue

            text = msg.content.strip()

            if not text:
                continue

            # Chỉ dịch tiếng Ý
            language = detect_language(text)

            if language != "it":
                continue

            try:
                translated = translate(text, "vi")

                translated_messages.append(
                    f"🇻🇳 **{msg.author.display_name}:**\n"
                    f"{translated}\n"
                    f"💬 *{text}*"
                )

            except Exception as e:
                print("Lỗi dịch tin cũ:", e)

        if not translated_messages:
            await interaction.followup.send(
                "Không tìm thấy tin nhắn tiếng Ý nào trong đoạn này.",
                ephemeral=True
            )
            return

        owner = await client.fetch_user(OWNER_USER_ID)

        # Discord giới hạn mỗi tin nhắn khoảng 2000 ký tự
        # nên bot tự chia thành nhiều DM nếu đoạn dịch dài
        current_message = (
            f"📜 **DỊCH {so_luong} TIN NHẮN GẦN NHẤT**\n\n"
        )

        for item in translated_messages:

            addition = item + "\n\n"

            if len(current_message) + len(addition) > 1900:
                await owner.send(current_message)
                current_message = addition
            else:
                current_message += addition

        if current_message.strip():
            await owner.send(current_message)

        await interaction.followup.send(
            f"✅ Đã kiểm tra {so_luong} tin nhắn gần nhất.\n"
            f"Đã gửi {len(translated_messages)} bản dịch tiếng Ý vào DM của bạn.",
            ephemeral=True
        )

    except Exception as e:
        print("Lỗi /dichcu:", e)

        await interaction.followup.send(
            "❌ Có lỗi khi lấy tin nhắn cũ.",
            ephemeral=True
        )


# =====================================
# CHỨC NĂNG CŨ - GIỮ NGUYÊN
# BẠN NHẮN TIẾNG VIỆT
# -> DỊCH SANG Ý CÔNG KHAI
# =====================================

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
