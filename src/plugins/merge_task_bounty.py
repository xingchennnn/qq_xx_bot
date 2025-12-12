from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
import asyncio
import re

# 目标机器人 QQ 号（小小）
TARGET_QQ = "3889001741"

# 全局状态存储
# 结构: {group_id: {"phase": "SECT" | "BOUNTY", "sect_state": "...", "bounty_state": "...", "stop_after": bool}}
merge_task_states = {}

# 中文数字转阿拉伯数字映射
CN_NUM = {
    '壹': 1, '贰': 2, '叁': 3, '肆': 4, '伍': 5,
    '陆': 6, '柒': 7, '捌': 8, '玖': 9, '拾': 10
}

# 辅助函数：宗门任务闭关等待
async def wait_and_resume_sect(bot: Bot, group_id: int):
    await asyncio.sleep(5 * 60)
    # 检查状态是否还在进行中且处于宗门阶段
    if group_id in merge_task_states and merge_task_states[group_id]["phase"] == "SECT":
        # 发送出关
        await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门出关")
        await asyncio.sleep(2)
        # 继续接取任务
        await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 宗门任务接取")

# 辅助函数：悬赏令等待结算
async def wait_and_settle_bounty(bot: Bot, group_id: int, minutes: int):
    await asyncio.sleep(minutes * 60)
    # 检查状态是否还在进行中且处于悬赏阶段
    if group_id in merge_task_states and merge_task_states[group_id]["phase"] == "BOUNTY":
        # 发送结算指令
        await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令结算")
        # 更新状态为等待结算结果
        merge_task_states[group_id]["bounty_state"] = "WAIT_SETTLEMENT"

# 1. 触发自动任务
auto_merge_task = on_command("自动任务", priority=5)

@auto_merge_task.handle()
async def handle_auto_merge_task(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    
    # 初始化状态，从宗门任务开始
    merge_task_states[group_id] = {
        "phase": "SECT",
        "sect_state": "RUNNING",
        "bounty_state": "IDLE",
        "stop_after": False
    }
    
    await auto_merge_task.send("开始自动任务：先执行宗门任务，完成后执行悬赏令。")
    await asyncio.sleep(1)
    # 发送指令开始接取宗门任务
    await auto_merge_task.send(MessageSegment.at(TARGET_QQ) + " 宗门任务接取")

# 2. 监听群消息，处理循环
listen_merge_task = on_message(priority=10, block=False)

@listen_merge_task.handle()
async def handle_merge_reply(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    user_id = str(event.user_id)
    
    # 只处理来自“小小”的消息，且当前群处于自动任务流程中
    if user_id != TARGET_QQ or group_id not in merge_task_states:
        return

    msg_text = event.get_plaintext()
    state_data = merge_task_states[group_id]
    current_phase = state_data["phase"]

    # ==================== 阶段一：宗门任务 ====================
    if current_phase == "SECT":
        # 检查是否在等待悬赏结束
        if state_data["sect_state"] == "WAITING_BOUNTY":
            if "悬赏壹" in msg_text or "结算" in msg_text:
                await asyncio.sleep(1)
                await listen_merge_task.send(MessageSegment.at(TARGET_QQ) + " 宗门闭关")
                state_data["sect_state"] = "RUNNING"
            return

        # 情况1: 接取成功，收到任务详情 -> 发送“宗门任务完成”
        if "当前任务" in msg_text or "任务查看" in msg_text:
            await asyncio.sleep(2)
            await listen_merge_task.send(MessageSegment.at(TARGET_QQ) + " 宗门任务完成")
            return

        # 情况2: 完成成功，收到奖励结算 -> 继续接取下一个
        if "恭喜道友完成宗门任务" in msg_text:
            await asyncio.sleep(2)
            await listen_merge_task.send(MessageSegment.at(TARGET_QQ) + " 宗门任务接取")
            return

        # 情况3: 次数耗尽 -> 切换到悬赏令阶段
        if "今日无法再获取宗门任务了" in msg_text:
            await listen_merge_task.send("今日宗门任务已全部完成，即将开始自动悬赏...")
            
            # 切换状态
            state_data["phase"] = "BOUNTY"
            state_data["bounty_state"] = "WAIT_LIST"
            
            await asyncio.sleep(2)
            # 启动悬赏令流程：先尝试出关（防止卡在闭关中），然后刷新
            await listen_merge_task.send(MessageSegment.at(TARGET_QQ) + " 宗门出关")
            await asyncio.sleep(2)
            await listen_merge_task.send(MessageSegment.at(TARGET_QQ) + " 出关")
            await asyncio.sleep(2)
            await listen_merge_task.send(MessageSegment.at(TARGET_QQ) + " 悬赏令刷新")
            return

        # 情况4: 任务失败 -> 宗门闭关
        if "道友兴高采烈的出门做任务" in msg_text:
            await asyncio.sleep(2)
            await listen_merge_task.send(MessageSegment.at(TARGET_QQ) + " 宗门闭关")
            return

        # 情况5: 尝试闭关时发现正在做悬赏 -> 等待悬赏结束
        if "道友现在在做悬赏令呢" in msg_text:
            state_data["sect_state"] = "WAITING_BOUNTY"
            return

        # 情况6: 已经在闭关中 -> 宗门出关
        if "道友在宗门闭关室中" in msg_text:
            await asyncio.sleep(2)
            await listen_merge_task.send(MessageSegment.at(TARGET_QQ) + " 宗门出关")
            return

        # 情况7: 闭关成功 -> 等待5分钟后出关并继续任务
        if "宗门闭关室 · 修炼界面" in msg_text:
            asyncio.create_task(wait_and_resume_sect(bot, group_id))
            return

    # ==================== 阶段二：悬赏令 ====================
    elif current_phase == "BOUNTY":
        bounty_state = state_data["bounty_state"]

        if bounty_state == "WAIT_LIST":
            if "请先悬赏令结算" in msg_text:
                await listen_merge_task.send("检测到未结算悬赏，正在自动结算...")
                await listen_merge_task.send(MessageSegment.at(TARGET_QQ) + " 悬赏令结算")
                state_data["bounty_state"] = "WAIT_SETTLEMENT"
                return

            if "今日悬赏令刷新次数已用尽" in msg_text:
                del merge_task_states[group_id]
                await listen_merge_task.send("今日悬赏次数已耗尽，自动任务全部结束")
                await listen_merge_task.finish(MessageSegment.at(TARGET_QQ) + " 闭关")
                return

            if "悬赏令进行中" in msg_text:
                time_match = re.search(r"预计剩余时间：(\d+)分钟", msg_text)
                minutes = 1
                if time_match:
                    minutes = int(time_match.group(1)) + 1
                
                await listen_merge_task.send(f"检测到悬赏进行中，将在 {minutes} 分钟后自动结算")
                asyncio.create_task(wait_and_settle_bounty(bot, group_id, minutes))
                state_data["bounty_state"] = "WAITING_TIMER"
                return

            if "天机悬赏令" in msg_text:
                # 检查剩余次数
                remain_match = re.search(r"今日剩余(\d+)次", msg_text)
                if remain_match:
                    remain_count = int(remain_match.group(1)) + 1
                    if remain_count <= 0:
                        del merge_task_states[group_id]
                        await listen_merge_task.finish("今日悬赏次数已耗尽，自动任务全部结束")
                        return
                    
                    if remain_count == 1:
                        state_data["stop_after"] = True
                    else:
                        state_data["stop_after"] = False

                # 解析悬赏令
                parts = msg_text.split("悬赏")[1:]
                best_bounty_index = -1
                max_reward = -1
                
                for part in parts:
                    if not part: continue
                    cn_idx = part[0]
                    if cn_idx not in CN_NUM: continue
                    idx = CN_NUM[cn_idx]
                    
                    reward_match = re.search(r"基础奖励(\d+)修为", part)
                    success_match = re.search(r"成功率[：:](\d+)%", part)

                    if reward_match:
                        reward = int(reward_match.group(1))
                        if success_match and int(success_match.group(1)) == 100:
                            reward = reward * 2
                        if reward > max_reward:
                            max_reward = reward
                            best_bounty_index = idx
                
                if best_bounty_index != -1:
                    state_data["bounty_state"] = "WAIT_CONFIRM"
                    await listen_merge_task.send(MessageSegment.at(TARGET_QQ) + f" 悬赏令接取{best_bounty_index}")
                else:
                    del merge_task_states[group_id]
                    await listen_merge_task.finish("未识别到有效的悬赏令信息")

        elif bounty_state == "WAIT_CONFIRM":
            if "悬赏令接取成功" in msg_text:
                time_match = re.search(r"预计时间：(\d+)分钟", msg_text)
                minutes = 10
                if time_match:
                    minutes = int(time_match.group(1))
                
                await listen_merge_task.send(f"接取成功，将在 {minutes} 分钟后自动结算")
                asyncio.create_task(wait_and_settle_bounty(bot, group_id, minutes))
                state_data["bounty_state"] = "WAITING_TIMER"

            elif "修仙令牌未生效" in msg_text and "悬赏令接取成功" not in msg_text:
                 pass

        elif bounty_state == "WAIT_SETTLEMENT":
            # 收到结算后的回复（假设任意回复都视为结算完成）
            if state_data.get("stop_after", False):
                 del merge_task_states[group_id]
                 await listen_merge_task.send("今日悬赏次数已耗尽，自动任务全部结束")
                 await asyncio.sleep(2)
                 await listen_merge_task.finish(MessageSegment.at(TARGET_QQ) + " 闭关")
            else:
                 await asyncio.sleep(2)
                 await listen_merge_task.send(MessageSegment.at(TARGET_QQ) + " 悬赏令刷新")
                 state_data["bounty_state"] = "WAIT_LIST"
