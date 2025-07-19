import json, discord, asyncio
from discord.ext import commands

### 設定読み込み ----------------------------------------------------
with open("config.json", encoding="utf-8") as f:
    cfg = json.load(f)

TOKEN            = cfg["token"]
INVITE_TO_ROLE   = cfg["mapping"]       # dict: code -> role name

### Bot 初期化 ------------------------------------------------------
intents = discord.Intents.none()
intents.guilds   = True
intents.members  = True                 # join を拾う
bot = commands.Bot(command_prefix="!", intents=intents)

### ★ join した瞬間に付与する --------------------------------------
@bot.event
async def on_member_join(member: discord.Member):
    # 直前に使われた招待を推測（24h キャッシュ）
    invite = get_recent_invite(member.guild.id, member.id)
    if invite and invite.code in INVITE_TO_ROLE:
        role_name = INVITE_TO_ROLE[invite.code]
        role      = discord.utils.get(member.guild.roles, name=role_name)
        if role:
            await member.add_roles(role)
            print(f"[+] {member} に {role_name} を付与")

### --- キャッシュまわり（簡易実装） -------------------------------
_invite_cache = {}   # guild_id -> {code: uses}

def get_recent_invite(gid, uid):
    """join 直後 (～10s) に呼ぶと、その人が踏んだ招待を返す"""
    return _temp_join_map.pop(uid, None)

_temp_join_map = {}  # uid -> inviteObj

@bot.event
async def on_invite_create(invite):
    # guild の全 invite を毎回取得してキャッシュ更新
    invites = await invite.guild.invites()
    _invite_cache[invite.guild.id] = {i.code: i.uses for i in invites}

@bot.event
async def on_member_join(member):
    # join 前後で invite.uses の差分をチェック
    await asyncio.sleep(1)                         # 反映待ち
    prev = _invite_cache.get(member.guild.id, {})
    invites_now = await member.guild.invites()
    for inv in invites_now:
        if inv.code in INVITE_TO_ROLE:
            if inv.uses > prev.get(inv.code, 0):
                _temp_join_map[member.id] = inv    # 後で回収
                break
    _invite_cache[member.guild.id] = {i.code: i.uses for i in invites_now}
    await on_member_join(member)                   # ロール付与本体

bot.run(TOKEN)
