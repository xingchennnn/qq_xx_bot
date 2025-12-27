from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
import asyncio
import re
import time
from enum import Enum, auto
from .common import TARGET_QQ, get_best_bounty, wait_and_settle_bounty

class TaskType(Enum):
    AUTO = "AUTO"                # 自动模式：宗门任务完成后自动接悬赏
    SECT_ONLY = "SECT_ONLY"      # 仅宗门任务：只做宗门任务
    BOUNTY_ONLY = "BOUNTY_ONLY"  # 仅悬赏令：只做悬赏令

# 全局状态存储：最小化，只保留任务类型和闭关时间
task_states = {}


async def seclusion_out(bot: Bot, group_id: int):
    """出关操作"""
    if group_id not in task_states:
        return

    state_data = task_states[group_id]
    
    # 检查闭关时长
    start_time = state_data.get("seclusion_start_time")
    if start_time:
        elapsed = time.time() - start_time
        if elapsed < 60:
            wait_time = 60 - elapsed + 2
            await bot.send_group_msg(group_id=group_id, message=f"闭关时间不足1分钟，等待 {int(wait_time)} 秒...")
            await asyncio.sleep(wait_time)
        state_data.pop("seclusion_start_time", None)
    
    # 优先发送出关指令，系统会自动判断当前的闭关类型
    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 出关")


async def start_sect_task(bot: Bot, group_id: int, task_type=TaskType.SECT_ONLY):
    """启动宗门任务流程"""
    if isinstance(task_type, str):
        try:
            task_type = TaskType(task_type)
        except ValueError:
            print("任务类型错误，使用默认 SECT_ONLY")
            pass

    task_states[group_id] = {
        "type": task_type,
        "seclusion_start_time": None,
        "doing_sect": True,  # 标记当前正在做宗门任务
        "waiting_seclusion": True,  # 标记已发送闭关，等待闭关成功响应
        "waiting_bounty_in_sect": False,  # 标记等待悬赏令进行中
        "settling_bounty_in_sect": False  # 标记当前正在结算宗门任务期间的悬赏令
    }
    
    # 发送闭关指令（不立即接取任务，等待闭关成功后由handle_task_reply处理）
    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 闭关")

    
async def start_bounty_task(bot: Bot, group_id: int, task_type=TaskType.BOUNTY_ONLY):
    """启动悬赏令流程"""
    if isinstance(task_type, str):
        try:
            task_type = TaskType(task_type)
        except ValueError:
            pass

    task_states[group_id] = {
        "type": task_type,
        "seclusion_start_time": None,
        "doing_sect": False,  # 标记不在做宗门任务，开始做悬赏令
        "waiting_seclusion": False,
        "waiting_bounty_in_sect": False,
        "settling_bounty_in_sect": False  # 标记当前正在结算宗门任务期间的悬赏令
    }
    
    # 出关
    await seclusion_out(bot, group_id)
    await asyncio.sleep(2)

    # 刷新悬赏令列表
    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令刷新")


async def handle_task_reply(bot: Bot, event: GroupMessageEvent):
    """处理小小的消息 - 直接根据消息内容响应，无需复杂状态机"""
    group_id = event.group_id
    user_id = str(event.user_id)

    # 检查是否是目标QQ且任务存在
    if user_id != TARGET_QQ or group_id not in task_states:
        return

    msg_text = event.get_plaintext()
    state_data = task_states[group_id]
    task_type = state_data["type"]


    # ==================== 宗门任务相关 ====================
    # 宗门任务完成
    if "恭喜道友完成宗门任务" in msg_text:
        await asyncio.sleep(2)
        await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务接取")
        return

    # 宗门任务做完了
    if "今日无法再获取宗门任务了" in msg_text:
        if task_type == TaskType.AUTO:
            await bot.send_group_msg(group_id=group_id, message="今日宗门任务已全部完成，即将开始自动悬赏...")
            await asyncio.sleep(2)
            # 转为悬赏令模式
            state_data["doing_sect"] = False
            await start_bounty_task(bot, group_id, task_type=TaskType.AUTO)
        else:
            del task_states[group_id]
            await bot.send_group_msg(group_id=group_id, message="今日宗门任务已全部完成")
        return

    # 没有接取宗门任务
    if "道友当前没有接取宗门任务" in msg_text:
        await asyncio.sleep(2)
        await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务接取")
        return

    # 宗门任务查询 - 检查是否需要刷新或完成
    if "当前任务" in msg_text or "任务查看" in msg_text or "任务接取" in msg_text or "任务刷新" in msg_text:
        if "除魔令" in msg_text or "狩猎邪修" in msg_text or "宗门密令" in msg_text:
            await asyncio.sleep(2)
            await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务完成")
        else:
            await asyncio.sleep(2)
            await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务刷新")
        return

    # 刷新冷却中
    if "时间还没到" in msg_text and "歇会歇会" in msg_text:
        match = re.search(r"还有 (\d+) 秒", msg_text)
        if match:
            seconds = int(match.group(1))
            wait_time = seconds + 2
            await bot.send_group_msg(group_id=group_id, message=f"宗门任务刷新冷却中，等待 {wait_time} 秒...")
            
            async def retry_sect_refresh():
                await asyncio.sleep(wait_time)
                if group_id in task_states:
                    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务刷新")
            
            asyncio.create_task(retry_sect_refresh())
        return

    # 气血不足
    if "道友兴高采烈的出门做任务" in msg_text:
        await asyncio.sleep(2)
        # 使用出关方法（同步等待到1分钟）
        await seclusion_out(bot, group_id)
        await asyncio.sleep(2)
        
        # 闭关并等待接取任务
        task_states[group_id]["waiting_seclusion"] = True
        await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 闭关")
        return

    # ==================== 闭关状态相关 ====================
    # 闭关成功
    if "闭关入定 · 修炼中" in msg_text:
        state_data["seclusion_start_time"] = time.time()
        # 如果是等待闭关后接取任务，则自动发送接取命令
        if state_data.get("waiting_seclusion", False):
            state_data["waiting_seclusion"] = False
            await asyncio.sleep(2)
            await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务接取")
        return

    # 已经在闭关
    if "道友现在在闭关呢" in msg_text or "已经在闭关中" in msg_text:
        # 检查宗门闭关还是普通闭关
        if "宗门闭关室" in msg_text or "道友现在正在宗门闭关室呢" in msg_text:
            state_data["seclusion_start_time"] = time.time()
        return

    # 宗门闭关室
    if "宗门闭关室 · 修炼界面" in msg_text or "道友在宗门闭关室中" in msg_text:
        state_data["seclusion_start_time"] = time.time()
        return

    # 出关完成
    if "闭关结算" in msg_text or "出关捷报" in msg_text:
        state_data["seclusion_start_time"] = None
        return

    # 没有闭关
    if "道友现在什么都没干" in msg_text:
        state_data["seclusion_start_time"] = None
        return
    
    if "道友现在在做悬赏令呢" in msg_text:
        state_data["seclusion_start_time"] = None
        # 如果在做宗门任务，直接结算悬赏令
        if state_data.get("doing_sect", False):
            state_data["waiting_bounty_in_sect"] = True  # 标记等待悬赏令进行中
            await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令结算")
        return

    # ==================== 悬赏令相关 ====================
    # 悬赏令相关的操作只在进行悬赏任务时处理（AUTO模式下宗门任务完成后，或BOUNTY_ONLY模式）
    
    # 如果正在做宗门任务，则需要特殊处理悬赏令进行中（等待后结算），但不处理其他悬赏令消息
    if state_data.get("doing_sect", False):
        # 悬赏令进行中 - 在做宗门任务期间，等待并结算
        if "悬赏令进行中" in msg_text and state_data.get("waiting_bounty_in_sect", False):
            time_match = re.search(r"预计剩余时间：(\d+)分钟", msg_text)
            minutes = 1
            if time_match:
                minutes = int(time_match.group(1)) + 1
            
            state_data["waiting_bounty_in_sect"] = False
            await bot.send_group_msg(group_id=group_id, message=f"悬赏令进行中，等待 {minutes} 分钟后自动结算...")
            
            async def wait_settle_and_resume_sect():
                await asyncio.sleep(minutes * 60)
                if group_id in task_states:
                    # 标记正在结算宗门任务期间的悬赏令
                    task_states[group_id]["settling_bounty_in_sect"] = True
                    # 结算悬赏令
                    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令结算")
            
            asyncio.create_task(wait_settle_and_resume_sect())
        return
    
    # 悬赏令刷新成功 - 显示列表
    if "天机悬赏令" in msg_text:
        remain_match = re.search(r"今日剩余(\d+)次", msg_text)
        if remain_match:
            remain_count = int(remain_match.group(1)) + 1
            if remain_count <= 0:
                del task_states[group_id]
                await bot.send_group_msg(group_id=group_id, message="今日悬赏次数已耗尽，任务结束")
                return
            # 最后一次后停止
            state_data["stop_after"] = (remain_count == 1)

        # 选择最优悬赏
        best_bounty_index = get_best_bounty(msg_text)
        if best_bounty_index != -1:
            await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + f" 悬赏令接取{best_bounty_index}")
        else:
            del task_states[group_id]
            await bot.send_group_msg(group_id=group_id, message="未识别到有效的悬赏令信息")
        return

    # 悬赏令接取成功
    if "悬赏令接取成功" in msg_text:
        time_match = re.search(r"预计时间：(\d+)分钟", msg_text)
        minutes = 10
        if time_match:
            minutes = int(time_match.group(1))
        
        await bot.send_group_msg(group_id=group_id, message=f"接取成功，将在 {minutes} 分钟后自动结算")
        
        async def wait_and_settle():
            await asyncio.sleep(minutes * 60)
            if group_id in task_states:
                await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令结算")
        
        asyncio.create_task(wait_and_settle())
        return

    # 悬赏令进行中 - 已经有悬赏在进行
    if "悬赏令进行中" in msg_text:
        time_match = re.search(r"预计剩余时间：(\d+)分钟", msg_text)
        minutes = 1
        if time_match:
            minutes = int(time_match.group(1)) + 1
        
        await bot.send_group_msg(group_id=group_id, message=f"检测到悬赏进行中，将在 {minutes} 分钟后自动结算")
        
        async def wait_and_settle():
            await asyncio.sleep(minutes * 60)
            if group_id in task_states:
                await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令结算")
        
        asyncio.create_task(wait_and_settle())
        return

    # 未结算的悬赏
    if "请先悬赏令结算" in msg_text:
        await bot.send_group_msg(group_id=group_id, message="检测到未结算悬赏，正在自动结算...")
        await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令结算")
        return

    # 悬赏令结算完成
    if "悬赏令结算" in msg_text:
        # 如果在做宗门任务期间的悬赏令结算完成
        if state_data.get("doing_sect", False) and state_data.get("settling_bounty_in_sect", False):
            state_data["settling_bounty_in_sect"] = False
            await asyncio.sleep(2)
            # 结算后，闭关并继续宗门任务
            state_data["waiting_seclusion"] = True
            await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 闭关")
            return
        # 如果在做宗门任务期间但不是结算阶段，忽略
        if state_data.get("doing_sect", False):
            return
        
        # 正常的悬赏令模式下的结算处理
        if state_data.get("stop_after", False):
            del task_states[group_id]
            await bot.send_group_msg(group_id=group_id, message="今日悬赏次数已耗尽，任务结束")
            await asyncio.sleep(2)
            await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 闭关")
        else:
            await asyncio.sleep(2)
            await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令刷新")
        return

    # 今日悬赏次数已用尽
    if "今日悬赏令刷新次数已用尽" in msg_text:
        del task_states[group_id]
        await bot.send_group_msg(group_id=group_id, message="今日悬赏次数已耗尽，任务结束")
        await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 闭关")
        return

    # 默认：打印未识别的消息
    print(f"接收到未处理的消息: {msg_text}")
