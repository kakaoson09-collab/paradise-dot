import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import datetime
import os
from threading import Thread
from flask import Flask

# ==========================================
# 24시간 호스팅용 웹 서버 (Render / Koyeb 무료 호스팅용)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "PARADISE Escrow Bot is Running Online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ==========================================
# 디스코드 봇 기본 설정
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


def check_staff(member: discord.Member) -> bool:
    """오너, 운영자, 관리자, 중개인 권한 확인"""
    if member.guild_permissions.administrator:
        return True
    for role in member.roles:
        if any(keyword in role.name for keyword in ["오너", "운영자", "관리자", "중개인", "중개자"]):
            return True
    return False


class EscrowControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    # 중개 종료 (채널 삭제)
    @discord.ui.button(label="중개 완료 및 채널 닫기", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_escrow_btn")
    async def close_escrow(self, interaction: discord.Interaction, button: Button):
        # 즉시 응답 지연 처리 (3초 초과 에러 방지)
        await interaction.response.defer(ephemeral=True)

        if not check_staff(interaction.user):
            await interaction.followup.send("❌ 중개인 및 관리자만 중개 채널을 종료할 수 있습니다.", ephemeral=True)
            return
        
        await interaction.followup.send("🔒 거래가 완료되었습니다. 5초 후 중개 채널이 삭제됩니다...")
        await asyncio.sleep(5)
        await interaction.channel.delete()


class EscrowCreateView(View):
    def __init__(self):
        super().__init__(timeout=None)

    # 1:1 중개 신청 버튼
    @discord.ui.button(label="중개 신청하기", style=discord.ButtonStyle.success, emoji="🏛️", custom_id="create_escrow_btn")
    async def create_escrow(self, interaction: discord.Interaction, button: Button):
        # ★ 핵심: 디스코드 3초 타임아웃 오류 방지 (즉시 응답 준비 신호 전송)
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user

        # 중복 중개 채널 검사
        for channel in guild.text_channels:
            if channel.name.startswith("중개-"):
                overwrite = channel.overwrites_for(user)
                if overwrite.view_channel:
                    await interaction.followup.send("❌ 이미 진행 중인 중개 채널이 있습니다! 기존 채널을 이용해 주세요.", ephemeral=True)
                    return

        # '🚨 | 실시간 중개 진행중' 카테고리 확인 및 생성
        category = discord.utils.get(guild.categories, name="🚨 | 실시간 중개 진행중")
        if not category:
            category = await guild.create_category("🚨 | 실시간 중개 진행중", position=0)

        # 채널 권한 설정 (신청자, 관리자/중개인, 봇만 보기)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        for role in guild.roles:
            if any(keyword in role.name for keyword in ["오너", "운영자", "관리자", "중개인", "중개자"]):
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel_name = f"중개-{user.name}"
        
        # 중개 채널 생성
        escrow_channel = await guild.create_text_channel(
            name=channel_name, 
            category=category, 
            position=0, 
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🏛️ PARADISE 공식 에스크로 중개 시스템",
            description=f"안녕하세요, {user.mention}님! **PARADISE 공식 안전 중개 서비스**입니다.\n\n"
                        f"📌 **중개 진행 양식 (채널에 입력해 주세요)**\n"
                        f"1. **구매자 / 판매자 멘션 (또는 디스코드 ID)**:\n"
                        f"2. **거래 물품 / 계정 종류**:\n"
                        f"3. **거래 금액**:\n"
                        f"4. **상대방 수수료 부담 여부**:\n\n"
                        f"⚠️ **주의사항**\n"
                        f"• 담당 중개인이 입장할 때까지 절대 미리 입금하거나 물품을 전달하지 마세요.\n"
                        f"• 사칭 계정 및 사설 사기에 주의하시기 바라며, 모든 거래는 이 채널 안에서만 진행됩니다.\n\n"
                        f"PARADISE Escrow Service",
            color=0xF1C40F
        )
        
        await escrow_channel.send(content=f"{user.mention} | 담당 중개진이 곧 입장합니다.", embed=embed, view=EscrowControlView())
        await interaction.followup.send(f"✅ 안전 중개 채널이 생성되었습니다: {escrow_channel.mention}", ephemeral=True)


@bot.event
async def on_ready():
    # Persistent View 등록 (봇이 재시작되어도 버튼이 먹통이 되지 않음)
    bot.add_view(EscrowCreateView())
    bot.add_view(EscrowControlView())
    print(f"로그인 완료: {bot.user} (ID: {bot.user.id})")
    print("PARADISE 안전 중개 봇 24시간 가동 준비 완료.")


# 중개 패널 생성 명령어 (!중개패널)
@bot.command(name="중개패널")
async def send_escrow_panel(ctx):
    if not ctx.author.guild_permissions.administrator:
        return
    await ctx.message.delete()
    
    embed = discord.Embed(
        title="🏛️ PARADISE 공식 에스크로 중개 시스템",
        description="안전하고 신속한 거래를 위해 아래 **[중개 신청하기]** 버튼을 눌러주세요.\n"
                    "생성된 비공개 채널에서 담당 중개진과 거래를 진행하실 수 있습니다.\n\n"
                    "• **운영 시간**: 24시간 전담 대기\n"
                    "• **보안 시스템**: 1:1 독립 비공개 채널에서 안전하게 거래 진행\n\n"
                    "PARADISE Escrow Service",
        color=0x1ABC9C
    )
    await ctx.send(embed=embed, view=EscrowCreateView())


if __name__ == "__main__":
    # 무료 웹 호스팅 서버 가동 (24시간 상시 가동용)
    keep_alive()
    
    # 환경변수 토큰 사용 또는 직접 토큰 입력
    TOKEN = os.environ.get("DISCORD_TOKEN", "MTU2Mjc3NTkyMzI1MjY1ODI3Nw.GANtIo.uFeS-HqYN8s7ylsPV31vp7OMuvdtNbUu2iOGyA")
    bot.run(TOKEN)