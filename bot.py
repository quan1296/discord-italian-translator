import os
import json
import asyncio
import discord
from discord import app_commands
from deep_translator import GoogleTranslator
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0

# =====================================
# CẤU HÌNH
# =====================================

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# File lưu danh sách người đã bật dịch
DATA_DIR = os.getenv("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)

ENABLED_USERS_FILE = os.path.join(
    DATA_DIR,
    "enabled_users.json"
)


# =====================================
# ĐỌC / LƯU DANH SÁCH NGƯỜI BẬT DỊCH
# =====================================

def load_enabled_users():
    try:
        if os.path.exists(ENABLED_USERS_FILE):
            with open(
                ENABLED_USERS_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                data = json.load(f)

            return set(int(user_id) for user_id in data)

    except Exception as e:
        print("Lỗi đọc enabled_users:", e)

    return set()


enabled_users = load_enabled_users()


def save_enabled_users():
    try:
        with open(
            ENABLED_USERS_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                list(enabled_users),
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:
        print("Lỗi lưu enabled_users:", e)


# =====================================
# NHẬN DIỆN NGÔN NGỮ
# =====================================

def detect_language(text):
    try:
        return detect(text)
    except:
        return None


# =====================================
# DỊCH NGÔN NGỮ
# =====================================

def translate_sync(text, target):
    return GoogleTranslator(
        source="auto",
        target=target
    ).translate(text)


async def translate(text, target):
    return await asyncio.to_thread(
        translate_sync,
        text,
        target
    )


# =====================================
# BOT ONLINE
# =====================================

@client.event
async def on_ready():

    try:
        await tree.sync()
        print("✅ Đã đồng bộ Slash Commands")

    except Exception as e:
        print("Lỗi sync command:", e)

    print(f"✅ Bot online: {client.user}")
    print(
        f"✅ Có {len(enabled_users)} người đang bật dịch"
    )


# =====================================
# /help
# HƯỚNG DẪN SONG NGỮ VIỆT + Ý
# =====================================

@tree.command(
    name="help",
    description="Hướng dẫn sử dụng • Guida all'utilizzo"
)
async def help_command(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="🇻🇳 🇮🇹 DICH ITALIAN",
        description=(
            "🇻🇳 **TIẾNG VIỆT**\n"
            "Bot dịch tự động giữa **Tiếng Việt** và **Tiếng Ý**.\n"
            "Mỗi người có thể tự bật hoặc tắt dịch cho "
            "tài khoản của mình.\n\n"

            "🇮🇹 **ITALIANO**\n"
            "Bot di traduzione automatica tra "
            "**vietnamita** e **italiano**.\n"
            "Ogni utente può attivare o disattivare "
            "la traduzione per il proprio account."
        )
    )

    embed.add_field(
        name="🟢 /batdich — Bật dịch • Attiva traduzione",
        value=(
            "🇻🇳 **Tiếng Việt:**\n"
            "Bật dịch tự động cho tài khoản của bạn.\n"
            "• Bạn nhắn tiếng Việt → bot tự dịch sang "
            "tiếng Ý công khai.\n"
            "• Có tin nhắn tiếng Ý → bot gửi bản dịch "
            "tiếng Việt vào DM riêng của bạn.\n\n"

            "🇮🇹 **Italiano:**\n"
            "Attiva la traduzione automatica per il tuo account.\n"
            "• Se scrivi in vietnamita → il bot traduce "
            "automaticamente in italiano nel canale.\n"
            "• Quando arriva un messaggio in italiano → "
            "riceverai la traduzione vietnamita tramite DM."
        ),
        inline=False
    )

    embed.add_field(
        name="🔴 /tatdich — Tắt dịch • Disattiva traduzione",
        value=(
            "🇻🇳 **Tiếng Việt:**\n"
            "Tắt dịch tự động cho tài khoản của bạn.\n"
            "Bạn sẽ không còn nhận bản dịch tự động qua DM.\n\n"

            "🇮🇹 **Italiano:**\n"
            "Disattiva la traduzione automatica.\n"
            "Non riceverai più le traduzioni automatiche "
            "tramite DM."
        ),
        inline=False
    )

    embed.add_field(
        name="📜 /dichcu — Dịch tin cũ • Traduci messaggi precedenti",
        value=(
            "🇻🇳 **Tiếng Việt:**\n"
            "Dịch từ **1 đến 100 tin nhắn gần nhất**.\n"
            "Ví dụ: `/dichcu 50`\n"
            "→ Bot kiểm tra 50 tin gần nhất và gửi các "
            "bản dịch tiếng Việt vào DM của bạn.\n\n"

            "🇮🇹 **Italiano:**\n"
            "Traduce da **1 a 100 messaggi recenti**.\n"
            "Esempio: `/dichcu 50`\n"
            "→ Il bot controlla gli ultimi 50 messaggi "
            "e invia le traduzioni in vietnamita tramite DM."
        ),
        inline=False
    )

    embed.add_field(
        name="🔒 Riêng tư • Privacy",
        value=(
            "🇻🇳 Bản dịch **Ý → Việt** được gửi riêng qua DM.\n"
            "Người khác trong server không nhìn thấy.\n\n"

            "🇮🇹 Le traduzioni **Italiano → Vietnamita** "
            "vengono inviate privatamente tramite DM.\n"
            "Gli altri utenti del server non possono vederle."
        ),
        inline=False
    )

    embed.set_footer(
        text="Dich Italian • Vietnamese ↔ Italian Translator"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =====================================
# /batdich
# MỖI NGƯỜI TỰ BẬT CHO CHÍNH MÌNH
# =====================================

@tree.command(
    name="batdich",
    description="Bật dịch tự động • Attiva traduzione"
)
async def batdich(
    interaction: discord.Interaction
):

    user_id = interaction.user.id

    if user_id in enabled_users:

        await interaction.response.send_message(
            "✅ 🇻🇳 Bạn đang bật dịch rồi.\n"
            "🇮🇹 La traduzione è già attiva.",
            ephemeral=True
        )

        return

    enabled_users.add(user_id)
    save_enabled_users()

    await interaction.response.send_message(
        "✅ **ĐÃ BẬT DỊCH • TRADUZIONE ATTIVATA**\n\n"

        "🇻🇳 Tiếng Việt → 🇮🇹 Tiếng Ý công khai.\n"
        "🇮🇹 Tiếng Ý → 🇻🇳 Tiếng Việt qua DM.\n\n"

        "🇮🇹 Vietnamita → Italiano nel canale.\n"
        "Italiano → Vietnamita tramite DM.",
        ephemeral=True
    )


# =====================================
# /tatdich
# MỖI NGƯỜI TỰ TẮT
# =====================================

@tree.command(
    name="tatdich",
    description="Tắt dịch tự động • Disattiva traduzione"
)
async def tatdich(
    interaction: discord.Interaction
):

    user_id = interaction.user.id

    if user_id not in enabled_users:

        await interaction.response.send_message(
            "ℹ️ 🇻🇳 Bạn hiện chưa bật dịch.\n"
            "🇮🇹 La traduzione non è attualmente attiva.",
            ephemeral=True
        )

        return

    enabled_users.remove(user_id)
    save_enabled_users()

    await interaction.response.send_message(
        "🔕 🇻🇳 Đã tắt dịch tự động cho bạn.\n"
        "🇮🇹 Traduzione automatica disattivata.",
        ephemeral=True
    )


# =====================================
# /dichcu
# DỊCH 1 → 100 TIN NHẮN GẦN NHẤT
# AI CŨNG DÙNG ĐƯỢC
# =====================================

@tree.command(
    name="dichcu",
    description="Dịch tin nhắn cũ • Traduci messaggi precedenti"
)
@app_commands.describe(
    so_luong="Số tin muốn dịch / Numero di messaggi (1-100)"
)
async def dichcu(
    interaction: discord.Interaction,
    so_luong: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        messages = []

        async for msg in interaction.channel.history(
            limit=so_luong
        ):
            messages.append(msg)

        # Sắp xếp từ cũ → mới
        messages.reverse()

        translated_messages = []

        for msg in messages:

            # Bỏ qua bot
            if msg.author.bot:
                continue

            text = (msg.content or "").strip()

            if not text:
                continue

            language = detect_language(text)

            # Chỉ dịch tin tiếng Ý
            if language != "it":
                continue

            try:

                translated = await translate(
                    text,
                    "vi"
                )

                if translated:

                    translated_messages.append(
                        f"🇻🇳 **{msg.author.display_name}:**\n"
                        f"{translated}\n\n"
                        f"💬 **Italiano:** {text}"
                    )

            except Exception as e:
                print(
                    "Lỗi dịch tin cũ:",
                    e
                )

        if not translated_messages:

            await interaction.followup.send(
                "ℹ️ 🇻🇳 Không tìm thấy tin nhắn tiếng Ý.\n"
                "🇮🇹 Nessun messaggio italiano trovato.",
                ephemeral=True
            )

            return

        # =====================================
        # GỬI DM CHO NGƯỜI DÙNG LỆNH
        # =====================================

        user = interaction.user

        header = (
            "📜 **DỊCH TIN NHẮN CŨ**\n"
            "**TRADUZIONE MESSAGGI PRECEDENTI**\n\n"
        )

        current_message = header

        for item in translated_messages:

            addition = (
                item
                + "\n\n"
                + "──────────────\n\n"
            )

            # Discord giới hạn khoảng 2000 ký tự
            if (
                len(current_message)
                + len(addition)
                > 1900
            ):

                await user.send(
                    current_message
                )

                current_message = addition

            else:

                current_message += addition

        if current_message.strip():

            await user.send(
                current_message
            )

        await interaction.followup.send(
            f"✅ 🇻🇳 Đã kiểm tra {so_luong} tin gần nhất "
            f"và gửi {len(translated_messages)} bản dịch vào DM.\n\n"

            f"🇮🇹 Controllati gli ultimi {so_luong} messaggi. "
            f"{len(translated_messages)} traduzioni inviate tramite DM.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ 🇻🇳 Bot không thể gửi DM cho bạn. "
            "Hãy bật nhận tin nhắn riêng.\n\n"

            "🇮🇹 Il bot non può inviarti messaggi privati. "
            "Abilita i messaggi diretti.",
            ephemeral=True
        )

    except Exception as e:

        print(
            "Lỗi /dichcu:",
            e
        )

        await interaction.followup.send(
            "❌ 🇻🇳 Có lỗi khi dịch tin nhắn cũ.\n"
            "🇮🇹 Errore durante la traduzione dei messaggi.",
            ephemeral=True
        )


# =====================================
# XỬ LÝ TIN NHẮN MỚI
# =====================================

@client.event
async def on_message(message):

    # Không xử lý tin nhắn của bot
    if message.author.bot:
        return

    text = (message.content or "").strip()

    if not text:
        return

    language = detect_language(text)

    sender_id = message.author.id


    # =====================================
    # NGƯỜI ĐÃ /batdich
    # NHẮN TIẾNG VIỆT
    # -> DỊCH SANG Ý CÔNG KHAI
    # =====================================

    if (
        sender_id in enabled_users
        and language == "vi"
    ):

        try:

            translated = await translate(
                text,
                "it"
            )

            if translated:

                await message.reply(
                    f"🇮🇹 **Italiano:**\n"
                    f"{translated}",
                    mention_author=False
                )

        except Exception as e:

            print(
                "Lỗi Việt → Ý:",
                e
            )

        return


    # =====================================
    # TIN NHẮN TIẾNG Ý
    # -> DM CHO TẤT CẢ NGƯỜI ĐÃ /batdich
    # =====================================

    if language == "it":

        try:

            translated = await translate(
                text,
                "vi"
            )

            if not translated:
                return

            for user_id in list(enabled_users):

                try:

                    user = await client.fetch_user(
                        user_id
                    )

                    await user.send(
                        f"🇻🇳 **{message.author.display_name}:**\n"
                        f"{translated}\n\n"
                        f"💬 **Italiano:** {text}"
                    )

                except discord.Forbidden:

                    print(
                        f"Không gửi được DM cho "
                        f"user {user_id}"
                    )

                except Exception as e:

                    print(
                        f"Lỗi gửi DM cho "
                        f"{user_id}: {e}"
                    )

        except Exception as e:

            print(
                "Lỗi Ý → Việt:",
                e
            )


# =====================================
# KHỞI ĐỘNG BOT
# =====================================

if not TOKEN:
    raise RuntimeError(
        "Không tìm thấy DISCORD_TOKEN."
    )

client.run(TOKEN)
