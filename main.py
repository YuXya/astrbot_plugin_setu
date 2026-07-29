from astrbot.api import logger
from astrbot.api.all import *
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core.message.message_event_result import MessageChain
import aiohttp
import asyncio
import math
from time import monotonic


async def image_obfus(img_data):
    """破坏图片哈希"""
    from PIL import Image as ImageP
    from io import BytesIO
    import random

    try:
        with BytesIO(img_data) as input_buffer:
            with ImageP.open(input_buffer) as img:
                if img.mode != "RGB":
                    img = img.convert("RGB")

                width, height = img.size
                pixels = img.load()

                points = []
                for _ in range(3):
                    while True:
                        x = random.randint(0, width - 1)  
                        y = random.randint(0, height - 1)   
                        if (x, y) not in points:
                            points.append((x, y))
                            break

                for x, y in points:
                    r, g, b = pixels[x, y]

                    r_change = random.choice([-1, 1])
                    g_change = random.choice([-1, 1])
                    b_change = random.choice([-1, 1])

                    new_r = max(0, min(255, r + r_change))
                    new_g = max(0, min(255, g + g_change))
                    new_b = max(0, min(255, b + b_change))

                    pixels[x, y] = (new_r, new_g, new_b)

                with BytesIO() as output:
                    img.save(output, format="PNG")
                    return output.getvalue()

    except Exception as e:
        logger.warning(f"破坏图片哈希时发生错误: {str(e)}")
        return img_data


@register(
    "astrbot_plugin_setu",
    "Omnisch",
    "Astrbot 色图插件，支持自定义配置与标签指定",
    "2.1.1",
    "https://github.com/Omnisch/astrbot_plugin_setu",
)
class PluginSetu(Star):
    USER_RATE_LIMIT_SECONDS = 60
    RATE_LIMIT_MESSAGE = (
        "调用过于频繁：普通用户每 60 秒只能获取 1 张图片，"
        "请 {seconds} 秒后再试。管理员调用次数不受限制。"
    )
    UNKNOWN_USER_MESSAGE = "无法识别当前用户，暂时无法获取图片。"

    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.exclude_ai = self.config.get("exclude_ai", False)
        self.image_hash_break = self.config.get("image_hash_break", False)
        self.send_forward = self.config.get("send_forward", False)
        self.r18 = self._normalize_r18(self.config.get("r18", 0))
        self.image_size = self.config.get("image_size", "original")
        self.image_info = self.config.get("image_info", "带标签的基本信息")
        self.detailed_info = ""
        self._last_user_calls: dict[tuple[str, str], float] = {}
        self._rate_limit_lock = asyncio.Lock()
        self._last_rate_limit_cleanup = monotonic()

    def _normalize_r18(self, r18) -> int:
        try:
            r18 = int(r18)
        except (TypeError, ValueError):
            logger.warning(f"无效的 R18 模式配置: {r18}，已回退为 0")
            return 0

        if r18 not in (0, 1, 2):
            logger.warning(f"无效的 R18 模式配置: {r18}，已回退为 0")
            return 0

        return r18

    def parse_tags(self, tags: str) -> list[list[str]]:
        """解析标签字符串"""
        if not tags:
            return []

        result = []
        for group in tags.split("&")[:3]:
            tags = [tag.strip() for tag in group.split(",")[:20]]
            if tags:
                result.append(tags)

        return result

    @filter.command_group("setu")
    def setu(self):
        pass

    def _unwrap_event(self, event):
        """兼容旧版 LLM Tool 误传 ContextWrapper 的情况。"""
        return getattr(getattr(event, "context", None), "event", event)

    async def _get_rate_limit_message(self, event: AstrMessageEvent):
        """占用普通用户的一次调用额度；管理员不受限制。"""
        if event.is_admin():
            return None

        sender_id = str(event.get_sender_id() or "").strip()
        if not sender_id:
            logger.warning("无法获取发送者 ID，已拒绝图片请求")
            return self.UNKNOWN_USER_MESSAGE

        platform_id_getter = getattr(event, "get_platform_id", None)
        if callable(platform_id_getter):
            platform_id = platform_id_getter()
        else:
            platform_id = event.get_platform_name()
        if not platform_id:
            platform_id = event.get_platform_name()

        user_key = (str(platform_id), sender_id)
        now = monotonic()

        async with self._rate_limit_lock:
            if (
                now - self._last_rate_limit_cleanup
                >= self.USER_RATE_LIMIT_SECONDS
            ):
                cutoff = now - self.USER_RATE_LIMIT_SECONDS
                self._last_user_calls = {
                    key: called_at
                    for key, called_at in self._last_user_calls.items()
                    if called_at > cutoff
                }
                self._last_rate_limit_cleanup = now

            last_call = self._last_user_calls.get(user_key)
            if last_call is not None:
                remaining = self.USER_RATE_LIMIT_SECONDS - (now - last_call)
                if remaining > 0:
                    return self.RATE_LIMIT_MESSAGE.format(
                        seconds=max(1, math.ceil(remaining))
                    )

            self._last_user_calls[user_key] = now

        return None

    def _build_image_chain(self, img_data, img_title, img_author, img_pid, img_tags):
        self.detailed_info = (
            f"标题：{img_title}\n"
            f"作者：{img_author}\n"
            f"PID：{img_pid}\n"
            f"标签：{' '.join(f'#{tag}' for tag in (img_tags or []))}"
        )

        if self.image_info == "只有图片":
            return [Image.fromBytes(img_data)]

        if self.image_info == "基本信息":
            return [
                Image.fromBytes(img_data),
                Plain(f"标题：{img_title}\n作者：{img_author}\nPID：{img_pid}"),
            ]

        return [
            Image.fromBytes(img_data),
            Plain(self.detailed_info),
        ]

    async def _fetch_setu_chain(self, tags: str = None, r18: int = 0):
        tags = self.parse_tags(tags)

        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "r18": r18,
                    "num": 1,
                    "size": [self.image_size],
                    "tag": tags,
                    "excludeAI": self.exclude_ai,
                    "proxy": "i.yuki.sh",
                }

                async with session.post(
                    "https://api.lolicon.app/setu/v2",
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as response:
                    response.raise_for_status()
                    resp = await response.json()

                if not resp["data"]:
                    return None, "未获取到图片"

                img = resp["data"][0]
                img_url = img["urls"][self.image_size]
                img_title = img["title"]
                img_author = img["author"]
                img_pid = img["pid"]
                img_tags = img["tags"]

                retry_count = 0
                while retry_count < 3:
                    try:
                        async with session.get(
                            img_url, timeout=aiohttp.ClientTimeout(total=120)
                        ) as img_response:
                            img_response.raise_for_status()
                            img_data = await img_response.read()

                        if self.image_hash_break:
                            img_data = await image_obfus(img_data)

                        return (
                            self._build_image_chain(
                                img_data,
                                img_title,
                                img_author,
                                img_pid,
                                img_tags,
                            ),
                            None,
                        )
                    except aiohttp.ClientError as e:
                        retry_count += 1
                        logger.warning(
                            f"图片下载失败，正在重试 ({retry_count}/3): {str(e)}"
                        )

                return None, f"获取图片失败，已重试 {retry_count} 次"

        except aiohttp.ClientError as e:
            logger.error(f"API 请求错误: {str(e)}")
            return None, f"API 请求错误: {str(e)}"
        except Exception as e:
            logger.error(f"发生未知错误: {str(e)}")
            return None, f"发生未知错误: {str(e)}"

    async def _get_setu(self, event: AstrMessageEvent, tags: str = None, r18: int = 0):
        event = self._unwrap_event(event)
        rate_limit_message = await self._get_rate_limit_message(event)
        if rate_limit_message:
            yield event.plain_result(rate_limit_message)
            return

        chain, error = await self._fetch_setu_chain(tags, r18)
        if error:
            yield event.plain_result(error)
            return

        send_forward = self.send_forward
        if send_forward and event.get_platform_name() != "aiocqhttp":
            send_forward = False
            logger.info("不支持当前平台，已禁用转发")

        if send_forward:
            node = Node(
                uin=event.get_self_id(),
                name="Setu",
                content=chain,
            )
            yield event.chain_result([node])
        else:
            yield event.chain_result(chain)

    @setu.command("get")
    async def get(self, event: AstrMessageEvent, tags: str = None):
        """随机色图"""
        async for result in self._get_setu(event, tags, r18=self.r18):
            yield result

    @filter.llm_tool(name="setu_get")
    async def llm_get_setu(self, event: AstrMessageEvent, tags: str = ""):
        '''获取并发送一张随机涩图，或根据标签获取一张特定涩图。当用户想要图片、涩图、来张图、指定标签图片时调用。

        调用限制（必须遵守）：普通用户按发送者独立限流，在任意连续 60 秒内最多调用一次；管理员调用次数不受限制。每次调用只允许查找并发送 1 张图片。服务端会强制执行；收到限流提示后不得在冷却时间内重试，也不得通过连续或并行重复调用来获取多张图片。

        Args:
             tags(string): 图片标签，可为空；只使用用户明确说出的标签，不得自行添加、联想、补充任何tag；中文或英文标签可翻译为适合日本插画网站检索的日语标签，但不得改变或扩展原意；多个 OR 标签用英文逗号分隔，多个 AND 条件用 & 分隔
        '''
        event = self._unwrap_event(event)
        rate_limit_message = await self._get_rate_limit_message(event)
        if rate_limit_message:
            return rate_limit_message

        chain, error = await self._fetch_setu_chain(tags or None, self.r18)
        if error:
            return error

        await event.send(MessageChain(chain=chain, type="tool_direct_result"))
        return "涩图已发送。"

    @setu.command("r18")
    async def get_r18(self, event: AstrMessageEvent, tags: str = None):
        """随机 R-18 色图"""
        async for result in self._get_setu(event, tags, r18=1):
            yield result

    @setu.command("details")
    async def last_details(self, event: AstrMessageEvent):
        """上一张色图的详细信息"""
        yield event.plain_result(self.detailed_info if self.detailed_info != "" else "无法获取上一张涩图的详细信息")

    @setu.command("help")
    async def help(self, event: AstrMessageEvent):
        """帮助"""
        yield event.plain_result(
            "使用方法：\n"
            "  /setu get 获取一张随机涩图\n"
            "  /setu get <tag> 获取特定标签的涩图\n"
            "  - 普通用户每 60 秒最多获取 1 张图片，管理员不限次数\n"
            "  - 使用 , 分隔 OR 条件,使用 & 分隔 AND 条件\n"
            "  - 标签中不得有空格，AND 条件最多 3 组，OR 条件每组最多 20 个\n"
            "  /setu details 查看上一张涩图的详细信息"
        )
