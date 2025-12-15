from nonebot import on_command, on_message
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
import re
import asyncio

# 目标机器人 QQ 号（小小）
TARGET_QQ = "3889001741"

# 全局状态存储
# 结构: {group_id: {"state": "WAIT_LIST" | "WAIT_CONFIRM" | "WAITING_TIMER" | "WAIT_SETTLEMENT", "stop_after": bool}}
auto_bounty_states = {}

# 中文数字转阿拉伯数字映射
CN_NUM = {
    '壹': 1, '贰': 2, '叁': 3, '肆': 4, '伍': 5,
    '陆': 6, '柒': 7, '捌': 8, '玖': 9, '拾': 10
}

async def wait_and_settle(bot: Bot, group_id: int, minutes: int):
    await asyncio.sleep(minutes * 60)
    # 发送结算指令
    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令结算")
    # 更新状态为等待结算结果
    if group_id in auto_bounty_states:
        auto_bounty_states[group_id]["state"] = "WAIT_SETTLEMENT"

# 1. 触发自动悬赏
auto_bounty = on_command("自动悬赏", rule=to_me(), priority=5)

@auto_bounty.handle()
async def handle_auto_bounty(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    
    if group_id in auto_bounty_states:
        await auto_bounty.finish("自动悬赏已在进行中，请勿重复开启")

    # 初始化状态
    auto_bounty_states[group_id] = {
        "state": "WAIT_LIST"
    }
    # 发送出关
    await auto_bounty.send(MessageSegment.at(TARGET_QQ) + " 宗门出关")
    await asyncio.sleep(2)
    await auto_bounty.send(MessageSegment.at(TARGET_QQ) + " 出关")
    await asyncio.sleep(2)


    
    # 发送指令刷新悬赏令
    await auto_bounty.send(MessageSegment.at(TARGET_QQ) + " 悬赏令刷新")


# 2. 监听群消息，处理状态机
listen_bounty = on_message(priority=10, block=False)

@listen_bounty.handle()
async def handle_bounty_reply(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    user_id = str(event.user_id)
    
    # 只处理来自“小小”的消息，且当前群处于自动悬赏流程中
    if user_id != TARGET_QQ or group_id not in auto_bounty_states:
        return

    state_data = auto_bounty_states[group_id]
    current_state = state_data["state"]
    msg_text = event.get_plaintext()

    if current_state == "WAIT_LIST":
        if "请先悬赏令结算" in msg_text:
            await listen_bounty.send("检测到未结算悬赏，正在自动结算...")
            await listen_bounty.send(MessageSegment.at(TARGET_QQ) + " 悬赏令结算")
            auto_bounty_states[group_id]["state"] = "WAIT_SETTLEMENT"
            return

        if "今日悬赏令刷新次数已用尽" in msg_text:
            del auto_bounty_states[group_id]
            await listen_bounty.send("今日悬赏次数已耗尽，自动悬赏结束")
            await listen_bounty.finish(MessageSegment.at(TARGET_QQ) + " 闭关")
            return

        if "悬赏令进行中" in msg_text:
            # Extract time
            time_match = re.search(r"预计剩余时间：(\d+)分钟", msg_text)
            minutes = 1
            if time_match:
                minutes = int(time_match.group(1)) + 1
            
            await listen_bounty.send(f"检测到悬赏进行中，将在 {minutes} 分钟后自动结算")
            
            # Start background task
            asyncio.create_task(wait_and_settle(bot, group_id, minutes))
            
            # Update state
            auto_bounty_states[group_id]["state"] = "WAITING_TIMER"
            return

        if "天机悬赏令" in msg_text:
            # 检查剩余次数
            remain_match = re.search(r"今日剩余(\d+)次", msg_text)
            if remain_match:
                remain_count = int(remain_match.group(1)) + 1
                if remain_count <= 0:
                    del auto_bounty_states[group_id]
                    await listen_bounty.finish("今日悬赏次数已耗尽，自动悬赏结束")
                    return
                # 如果剩余1次，说明做完这次就没了，标记为最后一次
                if remain_count == 1:
                    auto_bounty_states[group_id]["stop_after"] = True
                else:
                    auto_bounty_states[group_id]["stop_after"] = False

            # 解析悬赏令
            # 格式示例:
            # 悬赏壹·搜集琉璃天火液
            # ...
            # ✨基础奖励998530修为
            
            bounties = []
            
            # 使用正则匹配每一条悬赏
            # 假设每条悬赏以 "悬赏[中文数字]" 开头
            pattern = re.compile(r"悬赏([壹贰叁肆伍])·.*?\n.*?基础奖励(\d+)修为", re.DOTALL)
            
            # 由于 re.findall 在 DOTALL 模式下可能会跨越多个悬赏，我们需要小心分割
            # 或者我们可以先分割文本，再逐个解析
            
            # 简单分割方法：按 "悬赏" 分割，忽略第一段（头部）
            parts = msg_text.split("悬赏")[1:]
            
            best_bounty_index = -1
            max_reward = -1
            
            for part in parts:
                # 提取编号 (第一个字符)
                if not part:
                    continue
                
                cn_idx = part[0]
                if cn_idx not in CN_NUM:
                    continue
                    
                idx = CN_NUM[cn_idx]
                
                # 提取奖励
                reward_match = re.search(r"基础奖励(\d+)修为", part)
                # 成功率
                success_match = re.search(r"成功率[：:](\d+)%", part)

                if reward_match:
                    reward = int(reward_match.group(1))
                    
                    # 如果成功率为100%，触发双倍经验
                    if success_match and int(success_match.group(1)) == 100:
                        reward = reward * 2

                    if reward > max_reward:
                        max_reward = reward
                        best_bounty_index = idx
            
            if best_bounty_index != -1:
                # 接取奖励最高的悬赏
                auto_bounty_states[group_id]["state"] = "WAIT_CONFIRM"
                await listen_bounty.send(MessageSegment.at(TARGET_QQ) + f" 悬赏令接取{best_bounty_index}")
            else:
                # 未找到有效悬赏
                del auto_bounty_states[group_id]
                await listen_bounty.finish("未识别到有效的悬赏令信息")

    elif current_state == "WAIT_CONFIRM":
        if "悬赏令接取成功" in msg_text:
            # 提取预计时间
            time_match = re.search(r"预计时间：(\d+)分钟", msg_text)
            minutes = 10 # 默认值
            if time_match:
                minutes = int(time_match.group(1))
            
            await listen_bounty.send(f"接取成功，将在 {minutes} 分钟后自动结算")
            
            # 启动后台等待任务
            asyncio.create_task(wait_and_settle(bot, group_id, minutes))
            
            # 更新状态为等待计时结束
            auto_bounty_states[group_id]["state"] = "WAITING_TIMER"

        elif "修仙令牌未生效" in msg_text and "悬赏令接取成功" not in msg_text:
             # 失败情况处理
             pass

    elif current_state == "WAIT_SETTLEMENT":
        # 收到结算后的回复（假设任意回复都视为结算完成）
        # await listen_bounty.send("结算完成...")
        
        if auto_bounty_states[group_id].get("stop_after", False):
             del auto_bounty_states[group_id]
             await listen_bounty.send("今日悬赏次数已耗尽，自动悬赏结束")
             await asyncio.sleep(2)
             await listen_bounty.finish(MessageSegment.at(TARGET_QQ) + " 闭关")
        else:
             await asyncio.sleep(2)
             await listen_bounty.send(MessageSegment.at(TARGET_QQ) + " 悬赏令刷新")
             auto_bounty_states[group_id]["state"] = "WAIT_LIST"