from nonebot import on_command, on_message
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
import re
import asyncio

# 目标机器人 QQ 号（小小）
TARGET_QQ = "3889001741"

# 全局状态存储
# 结构: {group_id: {"state": "IDLE" | "WAIT_BAG" | "WAIT_PRICE", "items": [], "current_item_index": 0, "current_price": 0}}
# items 结构: [{"name": "紫猴花", "count": 2}, ...]
auto_sell_states = {}

# 1. 触发自动售卖
auto_sell = on_command("自动售卖", rule=to_me(), priority=5)

@auto_sell.handle()
async def handle_auto_sell(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    group_id = event.group_id
    
    # 解析参数
    arg_text = args.extract_plain_text().strip()
    price_offset = 0
    if arg_text:
        # 处理 "-10w" "10w" 这种格式
        # 替换单位
        clean_arg = arg_text.replace("w", "0000").replace("W", "0000").replace("万", "0000")
        try:
            price_offset = int(clean_arg)
        except ValueError:
            await auto_sell.finish("参数格式错误，请输入数字，例如：自动售卖 -10w")

    # 初始化状态
    auto_sell_states[group_id] = {
        "state": "WAIT_BAG",
        "items": [],
        "current_item_index": 0,
        "price_offset": price_offset
    }
    
    if price_offset != 0:
        action = "降价" if price_offset < 0 else "涨价"
        await auto_sell.send(f"已开启自动售卖，将在市场价基础上{action} {abs(price_offset)} 进行上架")

    # 发送指令获取背包
    await auto_sell.send(MessageSegment.at(TARGET_QQ) + " 药材背包")


# 2. 监听群消息，处理状态机
# priority=10 确保能拦截到消息
listen_xiaoxiao = on_message(priority=10, block=False)

@listen_xiaoxiao.handle()
async def handle_xiaoxiao_reply(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    user_id = str(event.user_id)
    
    # 只处理来自“小小”的消息，且当前群处于自动售卖流程中
    if user_id != TARGET_QQ or group_id not in auto_sell_states:
        return

    state_data = auto_sell_states[group_id]
    current_state = state_data["state"]
    msg_text = event.get_plaintext()

    # --- 状态：等待背包数据 ---
    if current_state == "WAIT_BAG":
        if "拥有药材" in msg_text:
            # 解析药材列表
            items = parse_bag_items(msg_text)
            if not items:
                await listen_xiaoxiao.send("未检测到可售卖药材，流程结束。")
                del auto_sell_states[group_id]
                return
            
            state_data["items"] = items
            state_data["current_item_index"] = 0
            state_data["state"] = "WAIT_PRICE"
            
            # 开始处理第一个物品：查询价格
            first_item = items[0]
            await asyncio.sleep(1) # 稍微延迟一下，避免刷屏太快
            await listen_xiaoxiao.send(MessageSegment.at(TARGET_QQ) + f" 坊市数据{first_item['name']}")
            
    # --- 状态：等待价格数据 ---
    elif current_state == "WAIT_PRICE":
        if "当前价格" in msg_text:
            # 解析价格
            price = parse_price(msg_text)
            if price:
                # 获取当前正在处理的物品
                idx = state_data["current_item_index"]
                items = state_data["items"]
                price_offset = state_data.get("price_offset", 0)
                
                if idx < len(items):
                    current_item = items[idx]
                    
                    # 计算最终价格
                    final_price = price + price_offset
                    if final_price < 1:
                        final_price = 1 # 价格不能低于1
                    
                    count = current_item["count"]
                    
                    # 构造上架指令
                    # 如果数量大于1，需要在后面加上数量
                    # 格式：确认坊市上架{药材} {价格} [数量]
                    cmd = f" 确认坊市上架{current_item['name']} {final_price}"
                    if count > 1:
                        cmd += f" {count}"
                    
                    # 稍微延迟
                    await asyncio.sleep(1)
                    await listen_xiaoxiao.send(MessageSegment.at(TARGET_QQ) + cmd)
                    
                    # 状态流转：等待上架结果（检查手续费是否足够）
                    state_data["state"] = "WAIT_SELL_RESULT"

    # --- 状态：等待上架结果 ---
    elif current_state == "WAIT_SELL_RESULT":
        # 检查是否成功或失败
        if "灵石不够支付手续费" in msg_text:
            await listen_xiaoxiao.send("检测到灵石不足支付手续费，自动售卖流程终止。")
            del auto_sell_states[group_id]
            return
            
        elif "成功上架" in msg_text or "上架物品数量" in msg_text:
            # 上架成功，继续下一个
            state_data["current_item_index"] += 1
            idx = state_data["current_item_index"]
            items = state_data["items"]
            
            if idx < len(items):
                # 还有下一个物品，继续查询价格
                next_item = items[idx]
                state_data["state"] = "WAIT_PRICE" # 回到等待价格状态
                await asyncio.sleep(2) 
                await listen_xiaoxiao.send(MessageSegment.at(TARGET_QQ) + f" 坊市数据{next_item['name']}")
            else:
                # 所有物品处理完毕
                await asyncio.sleep(1)
                await listen_xiaoxiao.send("所有药材已自动上架完毕！")
                del auto_sell_states[group_id]



def parse_bag_items(text):
    """
    解析背包文本，返回药材列表
    格式参考：
    名字：紫猴花
    拥有数量:2---炼金|坊市数据
    """
    items = []
    # 正则匹配 名字和数量
    # 名字：(.+)\n拥有数量:(\d+)
    matches = re.finditer(r"名字：(.+?)\s+拥有数量:(\d+)", text)
    for match in matches:
        name = match.group(1).strip()
        count = int(match.group(2))
        # 可以在这里过滤不需要卖的药材
        items.append({"name": name, "count": count})
    return items

def parse_price(text):
    """
    解析价格文本
    格式参考：
    当前价格: 290万 点击上架
    """
    # 匹配 "当前价格: 290万" 或 "当前价格: 2900000"
    match = re.search(r"当前价格:\s*(\d+)(万?)", text)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        if unit == "万":
            return num * 10000
        return num
    return None
