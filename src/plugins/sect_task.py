from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
import asyncio

# 目标机器人 QQ 号（小小）
TARGET_QQ = "3889001741"

# 全局状态存储
# 结构: {group_id: {"state": "RUNNING"}}
sect_task_states = {}

async def wait_and_resume_sect(bot: Bot, group_id: int):
    await asyncio.sleep(5 * 60)
    # 发送出关
    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门出关")
    await asyncio.sleep(2)
    # 继续接取任务
    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务接取")

# 1. 触发自动宗门任务
auto_sect = on_command("自动宗门任务", priority=5)

@auto_sect.handle()
async def handle_auto_sect(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    
    # 初始化状态
    sect_task_states[group_id] = {
        "state": "RUNNING"
    }
    
    # 发送指令开始接取任务
    await auto_sect.send(MessageSegment.at(TARGET_QQ) + " 宗门任务接取")


# 2. 监听群消息，处理循环
listen_sect = on_message(priority=10, block=False)

@listen_sect.handle()
async def handle_sect_reply(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    user_id = str(event.user_id)
    
    # 只处理来自“小小”的消息，且当前群处于自动宗门流程中
    if user_id != TARGET_QQ or group_id not in sect_task_states:
        return

    msg_text = event.get_plaintext()

    # 检查是否在等待悬赏结束
    if sect_task_states[group_id]["state"] == "WAITING_BOUNTY":
        # 如果收到悬赏刷新列表(含"悬赏壹")或结算信息，说明悬赏结束
        if "悬赏壹" in msg_text or "结算" in msg_text:
            await asyncio.sleep(1)
            await listen_sect.send(MessageSegment.at(TARGET_QQ) + " 宗门闭关")
            sect_task_states[group_id]["state"] = "RUNNING"
        return

    # 情况1: 接取成功，收到任务详情 -> 发送“宗门任务完成”
    # 关键词: "当前任务", "任务查看"
    if "当前任务" in msg_text or "任务查看" in msg_text:
        # 稍微延迟一点，模拟阅读或操作时间
        await asyncio.sleep(2)
        await listen_sect.send(MessageSegment.at(TARGET_QQ) + " 宗门任务完成")
        return

    # 情况2: 完成成功，收到奖励结算 -> 继续接取下一个
    # 关键词: "恭喜道友完成宗门任务"
    if "恭喜道友完成宗门任务" in msg_text:
        # 稍微延迟一点
        await asyncio.sleep(2)
        await listen_sect.send(MessageSegment.at(TARGET_QQ) + " 宗门任务接取")
        return

    # 情况3: 次数耗尽 -> 结束流程
    # 关键词: "今日无法再获取宗门任务了"
    if "今日无法再获取宗门任务了" in msg_text:
        del sect_task_states[group_id]
        await listen_sect.finish("今日宗门任务已全部完成")
        return

    # 情况4: 任务失败 -> 宗门闭关
    if "道友兴高采烈的出门做任务" in msg_text:
        await asyncio.sleep(2)
        await listen_sect.send(MessageSegment.at(TARGET_QQ) + " 宗门闭关")
        return

    # 情况5: 尝试闭关时发现正在做悬赏 -> 等待悬赏结束
    if "道友现在在做悬赏令呢" in msg_text:
        sect_task_states[group_id]["state"] = "WAITING_BOUNTY"
        return

    # 情况6: 已经在闭关中 -> 宗门出关
    if "道友在宗门闭关室中" in msg_text:
        await asyncio.sleep(2)
        await listen_sect.send(MessageSegment.at(TARGET_QQ) + " 宗门出关")
        return

    # 情况7: 闭关成功 -> 等待5分钟后出关并继续任务
    if "宗门闭关室 · 修炼界面" in msg_text:
        await listen_sect.send("闭关成功，将在5分钟后出关继续任务...")
        asyncio.create_task(wait_and_resume_sect(bot, group_id))
        return

    # 情况8: 已经在闭关中 (另一种提示) -> 宗门出关并继续任务
    if "道友现在正在宗门闭关室呢" in msg_text:
        await asyncio.sleep(2)
        await listen_sect.send(MessageSegment.at(TARGET_QQ) + " 宗门出关")
        await asyncio.sleep(2)
        await listen_sect.send(MessageSegment.at(TARGET_QQ) + " 宗门任务接取")
        return

