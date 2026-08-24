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

WEBHOOK_NAME = "Dich Italian Translator"


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
# KIỂM TRA BẢN DỊCH
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

    lowered = text.lower()

    for bad in bad_words:
        if bad.lower() in lowered:
            return False

    return True


# =========================================================
# DỊCH 1 - GOOGLE TRANSLATOR
# =========================================================

def google_translator_method(text, target):
    return GoogleTranslator(
        source="auto",
        target=target
    ).translate(text)


# =========================================================
# DỊCH 2 - GOOGLE HTTP
# =========================================================

def google_http_method(text, target):
    response = requests.get(
        "https://translate.googleapis.com/translate_a/single",
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
# DỊCH 3 - MYMEMORY
# =========================================================

def mymemory_method(text, target):
    source = detect_language(text)

    if not source:
        source = "en"

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
# FALLBACK DỊCH
# =========================================================

async def translate(text, target):

    methods = [
        google_translator_method,
        google_http_method,
        mymemory_method
    ]

    # Thử 2 vòng
    for round_number in range(2):

        for method in methods:

            try:
                result = await asyncio.to_thread(
                    method,
                    text,
                    target
                )

                if is_valid_translation(result):
                    return result.strip()

            except Exception as e:
                print(
                    f"⚠️ {method.__name__} lỗi:",
                    e
                )

        if round_number == 0:
            await asyncio.sleep(2)

    print("❌ Tất cả dịch vụ dịch đều thất bại.")

    return None


# =========================================================
# WEBHOOK
# =========================================================

async def get_translation_webhook(channel):

    # Nếu đang ở Thread thì webhook thuộc kênh cha
    if isinstance(channel, discord.Thread):

        parent = channel.parent

        if parent is None:
            return None

        webhooks = await parent.webhooks()

        for webhook in webhooks:
            if webhook.name == WEBHOOK_NAME:
                return webhook

        return await parent.create_webhook(
            name=WEBHOOK_NAME,
            reason="Automatic translation"
        )

    # Kênh chữ bình thường
    if isinstance(channel, discord.TextChannel):

        webhooks = await channel.webhooks()

        for webhook in webhooks:
            if webhook.name == WEBHOOK_NAME:
                return webhook

        return await channel.create_webhook(
            name=WEBHOOK_NAME,
            reason="Automatic translation"
        )

    return None


async def replace_with_italian(
    message,
    translated
):

    try:

        webhook = await get_translation_webhook(
            message.channel
        )

        if webhook is None:
            return False

        avatar_url = (
            message.author.display_avatar.url
            if message.author.display_avatar
            else None
        )

        # Nếu là Thread
        if isinstance(
            message.channel,
            discord.Thread
        ):

            await webhook.send(
                content=translated,
                username=message.author.display_name,
                avatar_url=avatar_url,
                thread=message.channel,
                allowed_mentions=discord.AllowedMentions.none()
            )

        else:

            await webhook.send(
                content=translated,
                username=message.author.display_name,
                avatar_url=avatar_url,
                allowed_mentions=discord.AllowedMentions.none()
            )

        # QUAN TRỌNG:
        # Chỉ xóa tin gốc sau khi webhook gửi thành công
        await message.delete()

        return True

    except discord.Forbidden:

        print(
            "❌ Bot thiếu quyền Manage Messages "
            "hoặc Manage Webhooks."
        )

        return False

    except Exception as e:

        print(
            "❌ Lỗi thay thế tin nhắn:",
            e
        )

        return False


# =========================================================
# BOT ONLINE
# =========================================================

@client.event
async def on_ready():

    try:
        await tree.sync()
        print("✅ Slash Commands đã đồng bộ")

    except Exception as e:
        print("❌ Lỗi sync:", e)

    print(f"✅ Bot online: {client.user}")


# =========================================================
# /NGONNGU
# =========================================================

@tree.command(
    name="ngonngu",
    description="Choose your translation language"
)
@app_commands.describe(
    ngon_ngu="Choose your language"
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

    data = get_user(
        interaction.user.id
    )

    data["language"] = ngon_ngu.value
    data["manual_language"] = True

    save_user_data()

    text_en = (
        f"✅ Your language is now "
        f"{ngon_ngu.name}."
    )

    if ngon_ngu.value == "en":
        response = text_en

    else:
        response = await translate(
            text_en,
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

    data = get_user(
        interaction.user.id
    )

    data["enabled"] = True

    save_user_data()

    target = (
        data.get("language")
        or "en"
    )

    text_en = (
        "✅ Translation enabled."
    )

    if target == "en":
        response = text_en

    else:
        response = await translate(
            text_en,
            target
        )

        if not response:
            response = text_en

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

    data = get_user(
        interaction.user.id
    )

    data["enabled"] = False

    save_user_data()

    target = (
        data.get("language")
        or "en"
    )

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
            response = text_en

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

    data = get_user(
        interaction.user.id
    )

    target = (
        data.get("language")
        or "en"
    )

    help_en = (
        "🌍 DICH ITALIAN\n\n"

        "🟢 /batdich\n"
        "Enable automatic translation.\n\n"

        "🔴 /tatdich\n"
        "Disable automatic translation.\n\n"

        "🌐 /ngonngu\n"
        "Choose your language.\n\n"

        "📜 /dichcu 1-100\n"
        "Translate previous Italian messages.\n\n"

        "💬 When enabled, a message written in "
        "a language other than Italian is translated "
        "into Italian and replaces the original message.\n\n"

        "🇮🇹 Italian messages are translated into "
        "your selected language."
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
    so_luong="Number of messages (1-100)"
)
async def dichcu(
    interaction: discord.Interaction,
    so_luong: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(
        ephemeral=True
    )

    data = get_user(
        interaction.user.id
    )

    target_language = data.get(
        "language"
    )

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

            if msg.webhook_id:
                # Webhook chứa bản Ý đã dịch
                # nên vẫn xem đó là tiếng Ý nếu cần
                pass

            if msg.author.id == interaction.user.id:
                continue

            text = (
                msg.content
                or ""
            ).strip()

            if not text:
                continue

            language = detect_language(
                text
            )

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

            await interaction.followup.send(
                "No Italian messages found.",
                ephemeral=True
            )

            return

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

        await interaction.followup.send(
            f"✅ {len(translated_messages)} "
            f"messages translated.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ I cannot send you private messages.",
            ephemeral=True
        )

    except Exception as e:

        print(
            "❌ Lỗi /dichcu:",
            e
        )

        await interaction.followup.send(
            "⚠️ Please try again.",
            ephemeral=True
        )


# =========================================================
# XỬ LÝ TIN NHẮN MỚI
# =========================================================

@client.event
async def on_message(message):

    # Bỏ qua DM
    if message.guild is None:
        return

    # Bỏ qua chính bot
    if message.author.bot:
        return

    # Bỏ qua tin do webhook tạo
    # tránh bot dịch lại bản dịch của chính mình
    if message.webhook_id:
        return

    text = (
        message.content
        or ""
    ).strip()

    if not text:
        return

    language = detect_language(
        text
    )

    if not language:
        return

    sender_id = message.author.id

    sender_data = get_user(
        sender_id
    )


    # =====================================================
    # NGƯỜI ĐÃ BẬT DỊCH
    # VIẾT NGÔN NGỮ KHÁC TIẾNG Ý
    #
    # -> DỊCH SANG Ý
    # -> ĐĂNG DƯỚI TÊN + AVATAR NGƯỜI GỬI
    # -> XÓA TIN GỐC
    # =====================================================

    if (
        sender_data.get("enabled")
        and language != "it"
    ):

        # Nếu chưa tự chọn /ngonngu
        # bot học ngôn ngữ người dùng
        if not sender_data.get(
            "manual_language"
        ):

            if (
                sender_data.get("language")
                != language
            ):

                sender_data[
                    "language"
                ] = language

                save_user_data()

        translated = await translate(
            text,
            "it"
        )

        # Nếu dịch thất bại
        # GIỮ NGUYÊN TIN GỐC
        if not translated:
            return

        await replace_with_italian(
            message,
            translated
        )

        return


    # =====================================================
    # CÓ NGƯỜI GỬI TIẾNG Ý
    #
    # -> DỊCH THEO NGÔN NGỮ
    # CỦA TỪNG USER ĐÃ BẬT
    # =====================================================

    if language == "it":

        for user_id, data in list(
            user_data.items()
        ):

            if not data.get("enabled"):
                continue

            if int(user_id) == sender_id:
                continue

            target_language = data.get(
                "language"
            )

            if not target_language:
                continue

            if target_language == "it":
                continue

            translated = await translate(
                text,
                target_language
            )

            if not translated:
                continue

            try:

                user = await client.fetch_user(
                    int(user_id)
                )

                await user.send(
                    f"**{message.author.display_name}:** "
                    f"{translated}"
                )

            except discord.Forbidden:

                print(
                    f"⚠️ Không gửi được DM "
                    f"cho {user_id}"
                )

            except Exception as e:

                print(
                    f"❌ Lỗi gửi DM cho "
                    f"{user_id}: {e}"
                )


# =========================================================
# KHỞI ĐỘNG
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN was not found."
    )


client.run(TOKEN)
