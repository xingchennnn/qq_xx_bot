from nonebot import on_command, on_message
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
import asyncio
from .common import TARGET_QQ
from .task_handler import TaskType, start_sect_task, start_bounty_task, handle_task_reply, task_states

# 1. 触发自动任务 (全流程)
auto_merge_task = on_command("自动任务", rule=to_me(), priority=5)

@auto_merge_task.handle()
async def handle_auto_merge_task(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    
    if group_id in task_states:
        await auto_merge_task.finish("任务已在进行中，请勿重复开启")

    await auto_merge_task.send("开始自动任务: 修仙签到->领丹药->宗门任务->悬赏令。")

    # 先执行签到和丹药领取
    await auto_merge_task.send(MessageSegment.at(TARGET_QQ) + " 修仙签到")
    await asyncio.sleep(2)
    await auto_merge_task.send(MessageSegment.at(TARGET_QQ) + " 宗门丹药领取")
    await asyncio.sleep(2)
    
    # 启动宗门任务，类型为 AUTO (完成后会自动接悬赏)
    await start_sect_task(bot, group_id, task_type=TaskType.AUTO)

# 4. 统一监听群消息
listen_tasks = on_message(priority=10, block=False)

@listen_tasks.handle()
async def handle_tasks(bot: Bot, event: GroupMessageEvent):
    await handle_task_reply(bot, event)
