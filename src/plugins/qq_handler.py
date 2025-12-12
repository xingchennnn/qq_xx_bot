from nonebot import on_command, on_message
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment

# 注册 -hello 命令
# 因为 .env 中配置了 COMMAND_START=["-"]，所以这里命令名写 "hello" 即可匹配 "-hello"
hello = on_command("hello", priority=5)

@hello.handle()
async def handle_hello(bot: Bot, event: Event):

    print("收到 -hello 命令" , event)
    # @ 发送者
    user_id = event.get_user_id()
    msg = MessageSegment.at(3889001741) + " 我的存档"
    
    # 发送回复
    await hello.finish(msg)

# 注册 -stop 命令
stop = on_command("stop", priority=5)

@stop.handle()
async def handle_stop(bot: Bot, event: Event):
    await stop.finish("机器人已关闭")


help = on_command("help", priority=5)
@help.handle()
async def handle_help(bot: Bot, event: Event):
    help_text = (
        "-hello : 向小小请求存档\n"
        # "-stop : 关闭机器人\n"
        "-help : 显示帮助信息\n"
        "-每日流程: 自动完成每日修仙签到、宗门丹药领取\n"
        "-自动宗门任务 : 自动完成宗门任务\n"
        "-自动悬赏 : 自动悬赏任务\n"
        "-自动售卖 : 自动售卖药材\n"

    )
    await help.finish(help_text)


# 注册机器人被 @ 的响应
# rule=to_me() 表示只有消息是发给机器人的（被 @ 或私聊）才会触发
# priority=99 优先级设低一点，避免拦截了正常的命令
# on_call = on_message(rule=to_me(), priority=99)

# @on_call.handle()
# async def handle_on_call(bot: Bot, event: Event):
#     # 获取用户发送的消息内容（纯文本）
#     user_msg = event.get_plaintext().strip()
    
#     # 目标机器人 QQ 号（小小）
#     target_qq = "3889001741"
    
#     # 构造转发消息：@小小 + 用户发送的内容
#     # 注意：这里去掉了用户消息中可能自带的 @机器人 部分，只保留指令内容
#     msg = MessageSegment.at(target_qq) + " " + user_msg
    
#     await on_call.finish(msg)



