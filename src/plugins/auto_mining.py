from nonebot import on_command, on_message
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
import asyncio
import random

from .common import TARGET_QQ


auto_mining_states = {}

auto_mining = on_command(
    "自动挖灵石",
    aliases={"自动灵界挖矿", "自动灵界挖灵石"},
    rule=to_me(),
    priority=5,
)
stop_auto_mining = on_command(
    "停止自动挖灵石",
    aliases={"停止灵界挖矿", "停止灵界挖灵石"},
    rule=to_me(),
    priority=5,
)


@auto_mining.handle()
async def handle_auto_mining(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id

    if group_id in auto_mining_states:
        await auto_mining.finish("自动挖灵石已在进行中，请勿重复开启")

    auto_mining_states[group_id] = {
        "mining_user_id": str(bot.self_id),
        "mining_count": 0,
    }

    await auto_mining.send("开始自动灵界挖灵石...")
    await asyncio.sleep(1)
    await bot.send_group_msg(
        group_id=group_id,
        message=MessageSegment.at(TARGET_QQ) + " 灵界挖灵石",
    )


@stop_auto_mining.handle()
async def handle_stop_auto_mining(event: GroupMessageEvent):
    group_id = event.group_id

    if group_id not in auto_mining_states:
        await stop_auto_mining.finish("当前没有正在进行的自动挖灵石")

    del auto_mining_states[group_id]
    await stop_auto_mining.finish("已停止自动挖灵石")


mining_reply = on_message(priority=10, block=False)


@mining_reply.handle()
async def handle_mining_reply(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    user_id = str(event.user_id)

    if user_id != TARGET_QQ or group_id not in auto_mining_states:
        return

    msg_text = event.get_plaintext()
    state_data = auto_mining_states[group_id]

    if "本次挖矿时长" in msg_text:
        return

    if not is_at_user(event, state_data["mining_user_id"]):
        return

    if "成功采集到" not in msg_text or "灵矿石储备" not in msg_text:
        return

    state_data["mining_count"] += 1
    await asyncio.sleep(random.uniform(1, 2))

    if group_id not in auto_mining_states:
        return

    await bot.send_group_msg(
        group_id=group_id,
        message=MessageSegment.at(TARGET_QQ) + " 灵界挖灵石",
    )


def is_at_user(event: GroupMessageEvent, user_id: str) -> bool:
    for segment in event.message:
        if segment.type == "at" and str(segment.data.get("qq")) == user_id:
            return True
    return False
