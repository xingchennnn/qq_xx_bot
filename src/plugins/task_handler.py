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

class TaskPhase(Enum):
    SECT = "SECT"      # 当前处于宗门任务阶段
    BOUNTY = "BOUNTY"  # 当前处于悬赏令阶段

class SectState(Enum):
    """ 宗门任务状态  """
    IDLE = "IDLE"                       # 空闲状态
    RUNNING = "RUNNING"                 # 正在进行宗门任务
    WAITING_BOUNTY = "WAITING_BOUNTY"   # 宗门任务中途触发了悬赏令，等待悬赏处理
    REFRESH_WAITING = "REFRESH_WAITING" # 宗门任务刷新冷却中（非邪修任务等待5分钟）

class BountyState(Enum):
    """ 悬赏令状态  """
    IDLE = "IDLE"                       # 空闲状态
    WAIT_LIST = "WAIT_LIST"             # 等待悬赏令列表刷新
    WAIT_CONFIRM = "WAIT_CONFIRM"       # 已发送接取请求，等待确认接取成功
    WAITING_TIMER = "WAITING_TIMER"     # 悬赏任务进行中，等待时间结束
    WAIT_SETTLEMENT = "WAIT_SETTLEMENT" # 等待结算（时间到后等待结算完成）

class seclusionState(Enum):
    UNKNOWN = "UNKNOWN"         # 未知状态，需要探测
    IDLE = "IDLE"               # 空闲状态（未闭关）
    RUNNING = "RUNNING"         # 正常闭关（发送“闭关”进入）
    SECT_RUNNING = "SECT_RUNNING" # 宗门闭关（发送“宗门闭关”进入）

# 全局状态存储
task_states = {}

def is_sect_phase(group_id: int): 
    """辅助函数 - 判断当前是否处于宗门任务阶段"""
    return group_id in task_states and task_states[group_id]["phase"] == TaskPhase.SECT

def is_bounty_phase(group_id: int): 
    """辅助函数 - 判断当前是否处于悬赏令阶段"""
    return group_id in task_states and task_states[group_id]["phase"] == TaskPhase.BOUNTY


async def check_seclusion_state(bot: Bot, group_id: int):
    """探测用户当前的闭关状态"""
    # 策略：发送“闭关”来探测状态
    # 1. 如果回复“闭关入定”，说明之前是空闲状态，现在进入了闭关 -> 状态确认为 RUNNING
    # 2. 如果回复“道友现在正在宗门闭关室呢”，说明之前在宗门闭关 -> 状态确认为 SECT_RUNNING
    # 3. 如果回复“道友现在在闭关呢”，说明之前在普通闭关 -> 状态确认为 RUNNING
    # 后续的状态判断和处理逻辑在 handle_task_reply 中进行
    # 这里我们设置一个临时状态，让 handle_task_reply 知道我们在探测
    if group_id in task_states:
        task_states[group_id]["seclusion_state"] = seclusionState.UNKNOWN
    
    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 闭关")

async def seclusion_out(bot: Bot, group_id: int):
    """出关操作"""
    if group_id not in task_states:
        return

    state_data = task_states[group_id]
    current_seclusion = state_data["seclusion_state"]

    # Check duration
    start_time = state_data.get("seclusion_start_time")
    if start_time:
        elapsed = time.time() - start_time
        if elapsed < 60:
            wait_time = 60 - elapsed + 2 # +2 buffer
            await bot.send_group_msg(group_id=group_id, message=f"闭关时间不足1分钟，等待 {int(wait_time)} 秒...")
            await asyncio.sleep(wait_time)
        # Clear start time
        state_data.pop("seclusion_start_time", None)
    
    if current_seclusion == seclusionState.SECT_RUNNING:
        await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门出关")
    elif current_seclusion == seclusionState.RUNNING:
        await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 出关")
 



async def start_sect_task(bot: Bot, group_id: int, task_type=TaskType.SECT_ONLY): # 启动宗门任务流程\
    """启动宗门任务流程"""
    if isinstance(task_type, str):
        try:
            task_type = TaskType(task_type)
        except ValueError:
            print("任务类型错误，使用默认 SECT_ONLY")
            pass

    task_states[group_id] = {
        "type": task_type,
        "phase": TaskPhase.SECT,
        "sect_state": SectState.RUNNING,
        "bounty_state": BountyState.IDLE,
        "stop_after": False,
        "seclusion_state": seclusionState.UNKNOWN # 初始状态未知
    }
    # 启动时探测状态
    await check_seclusion_state(bot, group_id)
    # 等待状态探测完成（简单等待一下，或者在 handle_task_reply 里处理接取逻辑）
    # 由于 check_seclusion_state 是异步发送消息，我们需要等待回复来更新状态
    # 但这里为了简化，我们假设探测后如果需要出关，会在 handle_task_reply 里处理
    # 不过，为了确保任务能接取，我们需要确保是空闲状态
    # 所以这里我们等待几秒，让探测消息有时间返回并处理
    await asyncio.sleep(3)
    
    # 根据探测到的状态决定是否出关
    # await seclusion_out(bot, group_id)
            
    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务接取")

    
async def start_bounty_task(bot: Bot, group_id: int, task_type=TaskType.BOUNTY_ONLY): # 启动悬赏令流程
    """启动悬赏令流程"""
    if isinstance(task_type, str):
        try:
            task_type = TaskType(task_type)
        except ValueError:
            pass

    task_states[group_id] = {
        "type": task_type, # 任务类型
        "phase": TaskPhase.BOUNTY, # 当前阶段
        "sect_state": SectState.IDLE, # 宗门任务状态
        "bounty_state": BountyState.WAIT_LIST, # 悬赏令状态
        "stop_after": False, # 是否悬赏后停止
        "seclusion_state": seclusionState.UNKNOWN, # 当前闭关状态
        "lock": asyncio.Lock() # 任务状态锁
    }
    
    # 启动悬赏令流程：先探测状态，然后刷新
    # await check_seclusion_state(bot, group_id)
    # await asyncio.sleep(3)
    
    await seclusion_out(bot, group_id)
    await asyncio.sleep(2)

    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令刷新")

async def handle_task_reply(bot: Bot, event: GroupMessageEvent): # 处理任务相关回复
    """处理小小的消息"""
    group_id = event.group_id
    user_id = str(event.user_id)

    #如果正在进行悬赏令或宗门任务
    if BountyState.IDLE == task_states[group_id]["bounty_state"] and SectState.IDLE == task_states[group_id]["sect_state"]:
        return

    # 检查是否是目标QQ且任务状态存在
    if user_id != TARGET_QQ or group_id not in task_states:
        return

    # 获取或初始化锁（为了兼容性，虽然 start_task 应该已经初始化了）
    lock = task_states[group_id].get("lock")
    if not lock:
        lock = asyncio.Lock()
        task_states[group_id]["lock"] = lock

    async with lock:
        # 在等待锁之后，重新检查状态是否存在
        if group_id not in task_states:
            return

        #获取当前小小的消息内容
        msg_text = event.get_plaintext()
        # 设置当前房间状态
        state_data = task_states[group_id]
    
        # ==================== 阶段一：宗门任务 ====================
        if   state_data["phase"] == TaskPhase.SECT:
            if "今日无法再获取宗门任务了" in msg_text: # 宗门任务做完了
                if state_data["type"] == TaskType.AUTO:  #自动任务中转悬赏
                 await bot.send_group_msg(group_id=group_id, message="今日宗门任务已全部完成，即将开始自动悬赏...")
                 await asyncio.sleep(2)
                 await start_bounty_task(bot, group_id, task_type=TaskType.AUTO)
                else: #仅宗门任务模式
                 del task_states[group_id]
                 await bot.send_group_msg(group_id=group_id, message="今日宗门任务已全部完成")
                return
        
            if state_data["sect_state"] == SectState.REFRESH_WAITING: # 等待刷新完成
             return
        

            if "时间还没到" in msg_text and "歇会歇会" in msg_text: 
                match = re.search(r"还有 (\d+) 秒", msg_text)
                if match:
                    seconds = int(match.group(1))
                    wait_time = seconds + 2 # Add small buffer
                
                    state_data["sect_state"] = SectState.REFRESH_WAITING
                    await bot.send_group_msg(group_id=group_id, message=f"宗门任务刷新冷却中，等待 {wait_time} 秒...")
                
                    async def retry_sect_refresh():
                        await asyncio.sleep(wait_time)
                        if group_id in task_states:
                            task_states[group_id]["sect_state"] = SectState.RUNNING
                            await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务刷新")
                
                    asyncio.create_task(retry_sect_refresh())
                return

            if "道友当前没有接取宗门任务" in msg_text:
                await asyncio.sleep(3)
                await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务接取")
                return

            if "当前任务" in msg_text or "任务查看" in msg_text or "任务接取" in msg_text or "任务刷新" in msg_text:
                if "除魔令" in msg_text or "狩猎邪修" in msg_text or "宗门密令" in msg_text:
                    await asyncio.sleep(2)
                    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务完成")
                else:
                    await asyncio.sleep(2)
                    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务刷新")
                return

            if "恭喜道友完成宗门任务" in msg_text: # 宗门任务完成
                await asyncio.sleep(2)
                await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务接取")
                return

            if "道友兴高采烈的出门做任务" in msg_text: #气血不足
                await asyncio.sleep(2)
                
                # 状态重置：任务失败意味着我们不在闭关状态，或者需要重新开始
                state_data["seclusion_state"] = seclusionState.IDLE
                state_data.pop("seclusion_start_time", None)

                # 直接闭关开始恢复
                await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 闭关")
                
                await bot.send_group_msg(group_id=group_id, message="状态欠佳，闭关恢复中(需等待至少60秒)...")

                async def recover_and_retry():
                    # 等待一下，确保闭关消息已处理且start_time已记录
                    await asyncio.sleep(5) 
                    if group_id in task_states:
                        await seclusion_out(bot, group_id)
                        await asyncio.sleep(2)
                        await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务完成")
                
                asyncio.create_task(recover_and_retry())
                return
        
            if "道友现在在做悬赏令呢" in msg_text:
                state_data["sect_state"] = SectState.WAITING_BOUNTY
                return

            if "道友现在正在宗门闭关室呢" in msg_text :
                # 探测结果：在宗门闭关中
                state_data["seclusion_state"] = seclusionState.SECT_RUNNING
                state_data["seclusion_start_time"] = time.time()
                return

            if "宗门闭关室 · 修炼界面" in msg_text:
                state_data["seclusion_state"] = seclusionState.SECT_RUNNING
                state_data["seclusion_start_time"] = time.time()
                return
            
            if "闭关入定 · 修炼中" in msg_text: 
                # 发送“闭关”成功，说明之前是空闲的，现在进入了闭关状态
                state_data["seclusion_state"] = seclusionState.RUNNING
                state_data["seclusion_start_time"] = time.time()
                # 既然是探测，我们不需要立即出关，除非后续逻辑需要
                # 但为了不影响任务接取，如果是在任务开始时的探测，可能需要出关
                # 这里我们只更新状态，具体的出关逻辑由任务流程控制
                # 不过，如果是因为探测而进入了闭关，通常我们希望保持空闲以便接任务
                # 所以这里还是出关比较好，或者在 start_task 里判断状态后出关
                # 为了简化，我们这里只更新状态。
                # 修正：如果是因为探测进入了闭关，为了不卡住流程，我们应该恢复到原来的空闲状态
                # await asyncio.sleep(60)
                # await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 出关")
                # state_data["seclusion_state"] = seclusionState.IDLE
                return
            
            if "道友现在在闭关呢" in msg_text:
                # 发送“闭关”失败，说明之前已经在普通闭关中
                state_data["seclusion_state"] = seclusionState.RUNNING
                return

            if "闭关结算" in msg_text:
                state_data["seclusion_state"] = seclusionState.IDLE
                return
            
            if "出关捷报" in msg_text:
                state_data["seclusion_state"] = seclusionState.IDLE
                # await asyncio.sleep(2)
                # await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务完成")
                return
            if "道友现在什么都没干" in msg_text: # 没有闭关
                state_data["seclusion_state"] = seclusionState.IDLE
                return
            else:
                # await bot.send_group_msg(group_id=group_id, message="宗门任务状态异常，任务终止 \n 错误语句：\n" + msg_text )
                # del task_states[group_id]

                print("接收到其他语句 \n 语句：\n" + msg_text )
                return

        # ==================== 阶段二：悬赏令 ====================
        elif  state_data["phase"] == TaskPhase.BOUNTY:
            bounty_state = state_data["bounty_state"]

            if bounty_state == BountyState.WAIT_LIST:
                if "请先悬赏令结算" in msg_text:
                    await bot.send_group_msg(group_id=group_id, message="检测到未结算悬赏，正在自动结算...")
                    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令结算")
                    state_data["bounty_state"] = BountyState.WAIT_SETTLEMENT
                    return
                if "悬赏令结算" in msg_text:
                    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令刷新")
                    return

                if "今日悬赏令刷新次数已用尽" in msg_text:
                    del task_states[group_id]
                    await bot.send_group_msg(group_id=group_id, message="今日悬赏次数已耗尽，任务结束")
                    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 闭关")
                    return

                if "悬赏令进行中" in msg_text:
                    time_match = re.search(r"预计剩余时间：(\d+)分钟", msg_text)
                    minutes = 1
                    if time_match:
                        minutes = int(time_match.group(1)) + 1
                    
                    await bot.send_group_msg(group_id=group_id, message=f"检测到悬赏进行中，将在 {minutes} 分钟后自动结算")
                    
                    async def bounty_check(gid):
                        if is_bounty_phase(gid):
                            task_states[gid]["bounty_state"] = BountyState.WAIT_SETTLEMENT
                            return True
                        return False

                    asyncio.create_task(wait_and_settle_bounty(bot, group_id, minutes, bounty_check))
                    state_data["bounty_state"] = BountyState.WAITING_TIMER
                    return

                if "天机悬赏令" in msg_text:
                    remain_match = re.search(r"今日剩余(\d+)次", msg_text)
                    if remain_match:
                        remain_count = int(remain_match.group(1)) + 1
                        if remain_count <= 0:
                            del task_states[group_id]
                            await bot.send_group_msg(group_id=group_id, message="今日悬赏次数已耗尽，任务结束")
                            return
                        state_data["stop_after"] = (remain_count == 1)

                    best_bounty_index = get_best_bounty(msg_text)
                    if best_bounty_index != -1:
                        state_data["bounty_state"] = BountyState.WAIT_CONFIRM
                        await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + f" 悬赏令接取{best_bounty_index}")
                    else:
                        del task_states[group_id]
                        await bot.send_group_msg(group_id=group_id, message="未识别到有效的悬赏令信息")

                if "道友在宗门闭关室中" in msg_text:
                    state_data["seclusion_state"] = seclusionState.SECT_RUNNING
                    await asyncio.sleep(2)
                    await seclusion_out(bot, group_id)
                    return
                if "已经在闭关中" in msg_text or "道友现在在闭关呢" in msg_text:
                    state_data["seclusion_state"] = seclusionState.RUNNING
                    await asyncio.sleep(2)
                    await seclusion_out(bot, group_id)
                    return

            elif bounty_state == BountyState.WAIT_CONFIRM:
                if "悬赏令接取成功" in msg_text:
                    time_match = re.search(r"预计时间：(\d+)分钟", msg_text)
                    minutes = 10
                    if time_match:
                        minutes = int(time_match.group(1))
                    
                    await bot.send_group_msg(group_id=group_id, message=f"接取成功，将在 {minutes} 分钟后自动结算")
                    
                    async def bounty_check(gid):
                        if is_bounty_phase(gid):
                            task_states[gid]["bounty_state"] = BountyState.WAIT_SETTLEMENT
                            return True
                        return False

                    asyncio.create_task(wait_and_settle_bounty(bot, group_id, minutes, bounty_check))
                    state_data["bounty_state"] = BountyState.WAITING_TIMER

            elif bounty_state == BountyState.WAIT_SETTLEMENT:
                if state_data.get("stop_after", False):
                    del task_states[group_id]
                    await bot.send_group_msg(group_id=group_id, message="今日悬赏次数已耗尽，任务结束")
                    await asyncio.sleep(2)
                    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 闭关")
                else:
                    await asyncio.sleep(2)
                    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令刷新")
                    state_data["bounty_state"] = BountyState.WAIT_LIST
            else :
                # await bot.send_group_msg(group_id=group_id, message="悬赏令指令异常 \n 错误语句：\n" + msg_text )
                print("接收到其他语句 \n 错误语句：\n" + msg_text )
                # del task_states[group_id]
                return