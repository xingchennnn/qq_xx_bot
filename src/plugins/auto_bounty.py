from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from .task_handler import start_bounty_task, task_states

# 1. 触发自动悬赏
auto_bounty = on_command("自动悬赏", rule=to_me(), priority=5)

@auto_bounty.handle()
async def handle_auto_bounty(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    
    if group_id in task_states:
        await auto_bounty.finish("任务已在进行中，请勿重复开启")

    await auto_bounty.send("开始自动悬赏任务...")
    # 启动悬赏任务，类型为 BOUNTY_ONLY
    await start_bounty_task(bot, group_id)
