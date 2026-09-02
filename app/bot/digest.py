from aiogram import Bot

from app.bot.presentation import card_keyboard, render_card
from app.schemas import OpportunityCard, OpportunityPage


class TelegramDigestSender:
    def __init__(self, bot: Bot, *, chat_id: int) -> None:
        self.bot = bot
        self.chat_id = chat_id

    async def send(self, card: OpportunityCard) -> None:
        page = OpportunityPage(
            card=card,
            page=0,
            has_previous=False,
            has_next=False,
        )
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=render_card(page),
            parse_mode="HTML",
            reply_markup=card_keyboard(page, mode="top"),
        )
