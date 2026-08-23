import os
import json
import asyncio
import requests
import discord

from discord import app_commands
from deep_translator import GoogleTranslator
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0


# =========================================================
# CẤU HÌNH
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

DATA_DIR = os.getenv("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)

USER_DATA_FILE = os.path.join(
    DATA_DIR,
    "user_translation_data.json"
)


# =========================================================
# NGÔN NGỮ
# =========================================================

LANGUAGE_NAMES = {
    "vi": "🇻🇳 Tiếng Việt",
    "en": "🇬🇧 English",
    "fr": "🇫🇷 Français",
    "es": "🇪🇸 Español",
    "de": "🇩🇪 Deutsch",
    "pt": "🇵🇹 Português",
    "ru": "🇷🇺 Русский",
    "uk": "🇺🇦 Українська",
    "ja": "🇯🇵 日本語",
    "ko": "🇰🇷 한국어",
    "zh-CN": "🇨🇳 中文",
    "th": "🇹🇭 ไทย",
    "id": "🇮🇩 Bahasa Indonesia",
    "tr": "🇹🇷 Türkçe",
    "pl": "🇵🇱 Polski",
    "nl": "🇳🇱 Nederlands",
    "ro": "🇷🇴 Română",
    "cs": "🇨🇿 Čeština",
    "el": "🇬🇷 Ελληνικά",
    "ar": "🇸🇦 العربية",
    "hi": "🇮🇳 हिन्दी"
}


# =========================================================
# DỮ LIỆU NGƯỜI DÙNG
# =========================================================

def load_user_data():

    try:
        if os.path.exists(USER_DATA_FILE):
            with open(
                USER_DATA_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                return json.load(f)

    except Exception as e:
        print("❌ Lỗi đọc dữ liệu:", e)

    return {}


user_data = load_user_data()


def save_user_data():

    try:
        with open(
            USER_DATA_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                user_data,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:
        print("❌ Lỗi lưu dữ liệu:", e)


def get_user(user_id):

    user_id = str(user_id)

    if user_id not in user_data:
        user_data[user_id] = {
            "enabled": False,
            "language": None,
            "manual_language": False
        }

    if "enabled" not in user_data[user_id]:
        user_data[user_id]["enabled"] = False

    if "language" not in user_data[user_id]:
        user_data[user_id]["language"] = None

    if "manual_language" not in user_data[user_id]:
        user_data[user_id]["manual_language"] = False

    return user_data[user_id]


# =========================================================
# NHẬN DIỆN NGÔN NGỮ
# =========================================================

def detect_language(text):

    try:
        return detect(text)

    except:
        return None


# =========================================================
# KIỂM TRA KẾT QUẢ DỊCH
# =========================================================

def is_valid_translation(result):

    if not result:
        return False

    text = str(result).strip()

    if not text:
        return False

    bad_words = [
        "Error 500",
        "500. That's an error",
        "500.That’s an error",
        "Server Error",
        "Please try again later",
        "That's all we know",
        "That’s all we know",
        "MYMEMORY WARNING"
    ]

    text_lower = text.lower()

    for bad in bad_words:
        if bad.lower() in text_lower:
            return False

    return True


# =========================================================
# PHƯƠNG PHÁP DỊCH 1
# GOOGLE TRANSLATOR
# =========================================================

def google_translator_method(text, target):

    return GoogleTranslator(
        source="auto",
        target=target
    ).translate(text)


# =========================================================
# PHƯƠNG PHÁP DỊCH 2
# GOOGLE ENDPOINT DỰ PHÒNG
# =========================================================

def google_http_method(text, target):

    response = requests.get(
        "https://translate.googleapis.com/"
        "translate_a/single",
        params={
            "client": "gtx",
            "sl": "auto",
            "tl": target,
            "dt": "t",
            "q": text
        },
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    if not data or not data[0]:
        return None

    result = ""

    for part in data[0]:

        if part and part[0]:
            result += part[0]

    return result


# =========================================================
# PHƯƠNG PHÁP DỊCH 3
# MYMEMORY
# =========================================================

def mymemory_method(text, target):

    source = detect_language(text)

    if not source:
        source = "en"

    # Một số mã cần chuẩn hóa
    if source == "zh-cn":
        source = "zh-CN"

    response = requests.get(
        "https://api.mymemory.translated.net/get",
        params={
            "q": text[:450],
            "langpair": f"{source}|{target}"
        },
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    return data.get(
        "responseData",
        {}
    ).get(
        "translatedText"
    )


# =========================================================
# HỆ THỐNG DỊCH FALLBACK
#
# GoogleTranslator
#       ↓ lỗi
# Google HTTP
#       ↓ lỗi
# MyMemory
#       ↓ lỗi
# Chờ rồi thử lại
# =========================================================

async def translate(text, target):

    methods = [
        google_translator_method,
        google_http_method,
        mymemory_method
    ]

    # Thử tối đa 2 vòng
    for round_number in range(2):

        for method in methods:

            try:

                result = await asyncio.to_thread(
                    method,
                    text,
                    target
                )

                if is_valid_translation(result):

                    print(
                        f"✅ Dịch thành công bằng "
                        f"{method.__name__}"
                    )

                    return result.strip()

                else:

                    print(
                        f"⚠️ {method.__name__} "
                        f"trả kết quả không hợp lệ."
                    )

            except Exception as e:

                print(
                    f"⚠️ {method.__name__} lỗi:",
                    e
                )

        # Nếu cả 3 lỗi
        # chờ rồi thử lại
        if round_number == 0:

            print(
                "🔄 Các dịch vụ đều lỗi. "
                "Đợi 2 giây rồi thử lại..."
            )

            await asyncio.sleep(2)

    print(
        "❌ Không thể dịch sau tất cả "
        "các phương pháp."
    )

    # Không gửi Error 500 ra Discord
    return None


# =========================================================
# BOT ONLINE
# =========================================================

@client.event
async def on_ready():

    try:

        await tree.sync()

        print("✅ Slash Commands đã đồng bộ")

    except Exception as e:

        print("❌ Lỗi sync commands:", e)

    print(f"✅ Bot online: {client.user}")


# =========================================================
# /NGONNGU
# =========================================================

@tree.command(
    name="ngonngu",
    description="Choose your translation language"
)
@app_commands.describe(
    ngon_ngu="Choose the language you want to use"
)
@app_commands.choices(
    ngon_ngu=[

        app_commands.Choice(
            name="🇻🇳 Tiếng Việt",
            value="vi"
        ),

        app_commands.Choice(
            name="🇬🇧 English",
            value="en"
        ),

        app_commands.Choice(
            name="🇫🇷 Français",
            value="fr"
        ),

        app_commands.Choice(
            name="🇪🇸 Español",
            value="es"
        ),

        app_commands.Choice(
            name="🇩🇪 Deutsch",
            value="de"
        ),

        app_commands.Choice(
            name="🇵🇹 Português",
            value="pt"
        ),

        app_commands.Choice(
            name="🇷🇺 Русский",
            value="ru"
        ),

        app_commands.Choice(
            name="🇺🇦 Українська",
            value="uk"
        ),

        app_commands.Choice(
            name="🇯🇵 日本語",
            value="ja"
        ),

        app_commands.Choice(
            name="🇰🇷 한국어",
            value="ko"
        ),

        app_commands.Choice(
            name="🇨🇳 中文",
            value="zh-CN"
        ),

        app_commands.Choice(
            name="🇹🇭 ไทย",
            value="th"
        ),

        app_commands.Choice(
            name="🇮🇩 Bahasa Indonesia",
            value="id"
        ),

        app_commands.Choice(
            name="🇹🇷 Türkçe",
            value="tr"
        ),

        app_commands.Choice(
            name="🇵🇱 Polski",
            value="pl"
        ),

        app_commands.Choice(
            name="🇳🇱 Nederlands",
            value="nl"
        ),

        app_commands.Choice(
            name="🇷🇴 Română",
            value="ro"
        ),

        app_commands.Choice(
            name="🇨🇿 Čeština",
            value="cs"
        ),

        app_commands.Choice(
            name="🇬🇷 Ελληνικά",
            value="el"
        ),

        app_commands.Choice(
            name="🇸🇦 العربية",
            value="ar"
        ),

        app_commands.Choice(
            name="🇮🇳 हिन्दी",
            value="hi"
        )
    ]
)
async def ngonngu(
    interaction: discord.Interaction,
    ngon_ngu: app_commands.Choice[str]
):

    data = get_user(interaction.user.id)

    data["language"] = ngon_ngu.value
    data["manual_language"] = True

    save_user_data()

    message_en = (
        f"✅ Your translation language has been set "
        f"to {ngon_ngu.name}."
    )

    if ngon_ngu.value == "en":

        response = message_en

    else:

        response = await translate(
            message_en,
            ngon_ngu.value
        )

        if not response:
            response = (
                f"✅ {ngon_ngu.name}"
            )

    await interaction.response.send_message(
        response,
        ephemeral=True
    )


# =========================================================
# /BATDICH
# =========================================================

@tree.command(
    name="batdich",
    description="Enable automatic translation"
)
async def batdich(
    interaction: discord.Interaction
):

    data = get_user(interaction.user.id)

    data["enabled"] = True

    save_user_data()

    target = data.get("language") or "en"

    text_en = (
        "✅ Translation enabled.\n"
        "Your messages will be translated into Italian.\n"
        "Italian messages will be translated for you."
    )

    if target == "en":

        response = text_en

    else:

        response = await translate(
            text_en,
            target
        )

        if not response:
            response = "✅ Translation enabled."

    await interaction.response.send_message(
        response,
        ephemeral=True
    )


# =========================================================
# /TATDICH
# =========================================================

@tree.command(
    name="tatdich",
    description="Disable automatic translation"
)
async def tatdich(
    interaction: discord.Interaction
):

    data = get_user(interaction.user.id)

    data["enabled"] = False

    save_user_data()

    target = data.get("language") or "en"

    text_en = (
        "🔕 Automatic translation disabled."
    )

    if target == "en":

        response = text_en

    else:

        response = await translate(
            text_en,
            target
        )

        if not response:
            response = "🔕 Translation disabled."

    await interaction.response.send_message(
        response,
        ephemeral=True
    )


# =========================================================
# /HELP
# =========================================================

@tree.command(
    name="help",
    description="Translation bot help"
)
async def help_command(
    interaction: discord.Interaction
):

    data = get_user(interaction.user.id)

    # Nếu biết ngôn ngữ của user
    # -> trả help bằng ngôn ngữ đó
    #
    # Nếu chưa biết
    # -> English

    target = data.get("language") or "en"

    help_en = (
        "🌍 DICH ITALIAN — TRANSLATION BOT\n\n"

        "This bot helps people who speak different "
        "languages communicate in Italian.\n\n"

        "🟢 /batdich\n"
        "Enable automatic translation.\n\n"

        "🔴 /tatdich\n"
        "Disable automatic translation.\n\n"

        "🌐 /ngonngu\n"
        "Choose the language you want to receive "
        "translations in.\n\n"

        "📜 /dichcu\n"
        "Translate previous Italian messages. "
        "You can check from 1 to 100 messages.\n\n"

        "💬 AUTOMATIC TRANSLATION\n"
        "When translation is enabled, messages you "
        "write in a language other than Italian are "
        "automatically translated into Italian "
        "in the channel.\n\n"

        "🇮🇹 ITALIAN MESSAGES\n"
        "Italian messages are translated into your "
        "selected language.\n\n"

        "💡 Use /ngonngu to manually select your "
        "language for more accurate translations."
    )

    if target == "en":

        help_text = help_en

    else:

        help_text = await translate(
            help_en,
            target
        )

        if not help_text:
            help_text = help_en

    await interaction.response.send_message(
        help_text,
        ephemeral=True
    )


# =========================================================
# /DICHCU
# =========================================================

@tree.command(
    name="dichcu",
    description="Translate previous Italian messages"
)
@app_commands.describe(
    so_luong="Number of messages to check (1-100)"
)
async def dichcu(
    interaction: discord.Interaction,
    so_luong: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(
        ephemeral=True
    )

    data = get_user(interaction.user.id)

    target_language = data.get("language")

    if not target_language:

        await interaction.followup.send(
            "⚠️ Please use `/ngonngu` first.",
            ephemeral=True
        )

        return

    try:

        messages = []

        async for msg in interaction.channel.history(
            limit=so_luong
        ):
            messages.append(msg)

        messages.reverse()

        translated_messages = []

        for msg in messages:

            if msg.author.bot:
                continue

            if msg.author.id == interaction.user.id:
                continue

            text = (msg.content or "").strip()

            if not text:
                continue

            language = detect_language(text)

            if language != "it":
                continue

            translated = await translate(
                text,
                target_language
            )

            if translated:

                translated_messages.append(
                    f"**{msg.author.display_name}:** "
                    f"{translated}"
                )

        if not translated_messages:

            text_en = (
                "No Italian messages were found "
                "in the selected history."
            )

            if target_language == "en":

                result = text_en

            else:

                result = await translate(
                    text_en,
                    target_language
                )

                if not result:
                    result = text_en

            await interaction.followup.send(
                result,
                ephemeral=True
            )

            return

        # Discord giới hạn độ dài message
        # nên tự chia nếu quá dài

        current_message = ""

        for item in translated_messages:

            addition = item + "\n"

            if (
                len(current_message)
                + len(addition)
                > 1900
            ):

                await interaction.user.send(
                    current_message
                )

                current_message = addition

            else:

                current_message += addition

        if current_message:

            await interaction.user.send(
                current_message
            )

        text_en = (
            f"✅ Translated "
            f"{len(translated_messages)} messages."
        )

        if target_language == "en":

            result = text_en

        else:

            result = await translate(
                text_en,
                target_language
            )

            if not result:
                result = (
                    f"✅ {len(translated_messages)}"
                )

        await interaction.followup.send(
            result,
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ I cannot send you private messages.",
            ephemeral=True
        )

    except Exception as e:

        # Chỉ log lỗi
        # không đưa Error 500 ra Discord

        print("❌ Lỗi /dichcu:", e)

        await interaction.followup.send(
            "⚠️ Please try again.",
            ephemeral=True
        )


# =========================================================
# XỬ LÝ TIN NHẮN
# =========================================================

@client.event
async def on_message(message):

    # Không xử lý message của bot
    if message.author.bot:
        return

    text = (message.content or "").strip()

    if not text:
        return

    language = detect_language(text)

    if not language:
        return

    sender_id = message.author.id

    sender_data = get_user(sender_id)


    # =====================================================
    # NGƯỜI ĐÃ BẬT DỊCH
    # NHẮN BẤT KỲ NGÔN NGỮ NÀO KHÁC Ý
    #
    # -> DỊCH SANG TIẾNG Ý CÔNG KHAI
    # =====================================================

    if (
        sender_data.get("enabled")
        and language != "it"
    ):

        # Nếu chưa chọn /ngonngu
        # bot học ngôn ngữ người dùng

        if not sender_data.get(
            "manual_language"
        ):

            if (
                sender_data.get("language")
                != language
            ):

                sender_data["language"] = language

                save_user_data()

        translated = await translate(
            text,
            "it"
        )

        # Chỉ gửi khi có bản dịch hợp lệ
        #
        # Không bao giờ gửi Error 500
        # ra channel

        if translated:

            await message.channel.send(
                f"🇮🇹 {translated}"
            )

        return


    # =====================================================
    # CÓ TIN NHẮN TIẾNG Ý
    #
    # -> DỊCH CHO TỪNG USER ĐANG BẬT
    # -> THEO NGÔN NGỮ CỦA TỪNG NGƯỜI
    # =====================================================

    if language == "it":

        for user_id, data in list(
            user_data.items()
        ):

            # User chưa bật dịch
            if not data.get("enabled"):
                continue

            # Không gửi lại cho chính người viết
            if int(user_id) == sender_id:
                continue

            target_language = data.get(
                "language"
            )

            if not target_language:
                continue

            # Người dùng dùng tiếng Ý
            # thì không cần dịch
            if target_language == "it":
                continue

            translated = await translate(
                text,
                target_language
            )

            # Nếu dịch lỗi
            # không gửi lỗi cho user

            if not translated:
                continue

            try:

                user = await client.fetch_user(
                    int(user_id)
                )

                # BẢN DỊCH RIÊNG GỌN
                await user.send(
                    f"**{message.author.display_name}:** "
                    f"{translated}"
                )

            except discord.Forbidden:

                print(
                    f"⚠️ User {user_id} "
                    f"đang chặn DM."
                )

            except Exception as e:

                print(
                    f"❌ Lỗi gửi cho "
                    f"{user_id}: {e}"
                )


# =========================================================
# KHỞI ĐỘNG BOT
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN was not found."
    )


client.run(TOKEN)
