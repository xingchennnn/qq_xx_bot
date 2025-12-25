import re
import asyncio
from nonebot.adapters.onebot.v11 import Bot, MessageSegment

# 目标机器人 QQ 号（小小）
TARGET_QQ = "3889001741"

# 中文数字转阿拉伯数字映射
CN_NUM = {
    '壹': 1, '贰': 2, '叁': 3, '肆': 4, '伍': 5,
    '陆': 6, '柒': 7, '捌': 8, '玖': 9, '拾': 10
}

def get_best_bounty(msg_text: str):
    """解析悬赏令并返回最佳悬赏索引"""
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
    return best_bounty_index


async def wait_and_settle_bounty(bot: Bot, group_id: int, minutes: int, check_func=None):
    """悬赏令等待结算"""
    await asyncio.sleep(minutes * 60)
    # 如果提供了检查函数，则先检查是否需要继续
    if check_func and not check_func(group_id):
        return
        
    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(TARGET_QQ) + " 悬赏令结算")
