from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from .task_handler import TaskType, start_sect_task, task_states

# 1. 触发自动宗门任务
auto_sect = on_command("自动宗门任务", rule=to_me(), priority=5)

@auto_sect.handle()
async def handle_auto_sect(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    
    if group_id in task_states:
        await auto_sect.finish("任务已在进行中，请勿重复开启")

    await auto_sect.send("开始自动宗门任务...")
    # 启动宗门任务，类型为 SECT_ONLY
    await start_sect_task(bot, group_id, task_type=TaskType.SECT_ONLY)
