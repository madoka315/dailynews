import asyncio
import datetime

from hoshino import Service, aiorequests
from hoshino.typing import MessageSegment, CQEvent, HoshinoBot

sv = Service('dailynews', enable_on_default=False, help_='''每日早报
启用后会在每天早上发送一份早报
[@bot 今日早报] （测试用）手动发送一份早报''')

API = 'https://60s.viki.moe/v2/60s'


async def fetch_news_image():
    last_err = None
    for i in range(10):
        try:
            resp = await aiorequests.get(API, timeout=15)
            info = await resp.json()
            data = info.get('data') or {}
            if info.get('code') != 200 or not data.get('image'):
                raise ValueError(f'60s api 异常返回: {str(info)[:120]}')
            if data.get('date') != str(datetime.date.today()):
                raise ValueError(f'早报图源疑似停更: 接口日期 {data.get("date")}')
            return data['image']
        except Exception as e:
            last_err = e
            sv.logger.warning(f'daily news error (attempt {i+1}/10): {type(e).__name__} {e}')
            await asyncio.sleep(30)
    raise last_err


@sv.scheduled_job('cron', hour='8', minute='40', jitter=50)
async def autonews():
    try:
        img = await fetch_news_image()
    except Exception as e:
        sv.logger.error(f'daily news error: {type(e).__name__} {e}')
        return
    await sv.broadcast(MessageSegment.image(img, cache=True), 'dailynews')


@sv.on_fullmatch('今日早报', only_to_me=True)
async def handnews(bot: HoshinoBot, ev: CQEvent):
    try:
        img = await fetch_news_image()
    except Exception as e:
        sv.logger.error(f'daily news error: {type(e).__name__} {e}')
        await bot.send(ev, '早报获取失败，请稍后再试')
        return
    await bot.send(ev, MessageSegment.image(img, cache=True))
