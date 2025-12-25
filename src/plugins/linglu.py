from nonebot import on_command, on_message
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
import asyncio
import re
from .common import TARGET_QQ

# 状态存储
linglu_states = {}

# 开启自动灵露收集
auto_linglu = on_command("灵露收集", rule=to_me(), priority=5)

@auto_linglu.handle()
async def handle_auto_linglu(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    
    if group_id in linglu_states:
        await auto_linglu.finish("灵露收集任务已在进行中")

    linglu_states[group_id] = True
    await auto_linglu.send("开始自动灵露收集，直到收益归零...")
    await asyncio.sleep(1)
    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 收集灵露")

# 监听回复
linglu_reply = on_message(priority=99)

@linglu_reply.handle()
async def handle_linglu_reply(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    user_id = str(event.user_id)
    msg = event.get_plaintext()

    # 仅处理目标机器人的消息，且当前群组处于灵露收集状态
    if user_id != TARGET_QQ or group_id not in linglu_states:
        return

    # 检查是否是灵露收集的回复
    if "蛇神恒晶" in msg and "蛇神灵露" in msg:
        # 检查是否为0
        # 格式示例：获得0个蛇神恒晶，0个蛇神灵露
        # 使用正则提取数字
        
        # 简单判断字符串是否存在
        if "获得0个蛇神恒晶" in msg and "0个蛇神灵露" in msg:
            del linglu_states[group_id]
            await bot.send_group_msg(group_id=group_id, message="灵露收集完成，收益已归零。")
        else:
            # 继续收集
            await asyncio.sleep(2) # 稍微延迟一点避免刷屏过快
            await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 收集灵露")
