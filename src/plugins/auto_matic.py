from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
import asyncio

# 目标机器人 QQ 号（小小）
TARGET_QQ = "3889001741"

daily_routine = on_command("每日流程",rule=to_me(), priority=5)

@daily_routine.handle()
async def handle_daily_routine(bot: Bot, event: GroupMessageEvent):
    # 1. 修仙签到
    await daily_routine.send(MessageSegment.at(TARGET_QQ) + " 修仙签到")
    await asyncio.sleep(2)
    
    # 2. 宗门丹药领取
    await daily_routine.send(MessageSegment.at(TARGET_QQ) + " 宗门丹药领取")
    await asyncio.sleep(2)
    
    # 3. 灵庄结算
    # await daily_routine.send(MessageSegment.at(TARGET_QQ) + " 灵庄结算")
    
    await daily_routine.finish("每日流程指令已发送完毕")
