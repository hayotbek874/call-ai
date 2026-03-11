import json

from redis.asyncio import Redis

from src.clients.openai_client import OpenAIClient
from src.core.logging import get_logger, mask_phone
from src.repositories.conversation_repository import ConversationRepository
from src.services.ai.prompt_builder import build_system_prompt

logger = get_logger(__name__)

class ContextService:
    MESSAGES_KEY = "ctx:msg:{channel}:{phone}"
    SUMMARY_KEY = "ctx:summary:{channel}:{phone}"
    MAX_MESSAGES = 10

    def __init__(self, redis: Redis, repo: ConversationRepository, openai: OpenAIClient):
        self._redis = redis
        self._repo = repo
        self._openai = openai

    def _msg_key(self, channel: str, phone: str) -> str:
        return self.MESSAGES_KEY.format(channel=channel, phone=phone)

    def _sum_key(self, channel: str, phone: str) -> str:
        return self.SUMMARY_KEY.format(channel=channel, phone=phone)

    async def clear_channel(self, phone: str, channel: str) -> None:
        await logger.info("clear_channel", phone=mask_phone(phone), channel=channel)
        pipe = self._redis.pipeline()
        pipe.delete(self._msg_key(channel, phone))
        pipe.delete(self._sum_key(channel, phone))
        await pipe.execute()

    async def get_messages(self, phone: str, channel: str) -> list[dict]:
        await logger.debug("get_messages", phone=mask_phone(phone), channel=channel)
        key = self._msg_key(channel, phone)
        raw = await self._redis.lrange(key, 0, -1)
        if raw:
            await logger.debug("messages_from_cache", phone=mask_phone(phone), count=len(raw))
            return [json.loads(m) for m in raw]

        if channel == "voice":
            return []

        messages = await self._repo.get_last_messages_by_phone(phone, channel, self.MAX_MESSAGES)
        if messages:
            pipe = self._redis.pipeline()
            for m in messages:
                pipe.rpush(key, json.dumps({"role": m.role, "content": m.content}))
            pipe.expire(key, 3600)
            await pipe.execute()
            return [{"role": m.role, "content": m.content} for m in messages]
        return []

    async def get_summary(self, phone: str, channel: str) -> str | None:
        await logger.debug("get_summary", phone=mask_phone(phone), channel=channel)

        if channel == "voice":
            return None

        cached = await self._redis.get(self._sum_key(channel, phone))
        if cached:
            await logger.debug("summary_from_cache", phone=mask_phone(phone))
            return cached if isinstance(cached, str) else cached.decode()
        summary = await self._repo.get_last_summary(phone, channel)
        await logger.debug("summary_from_db", phone=mask_phone(phone), found=summary is not None)
        return summary

    async def append(
        self, phone: str, role: str, content: str,
        channel: str = "telegram", intent: str | None = None,
    ) -> None:
        await logger.info(
            "append_message",
            phone=mask_phone(phone),
            role=role,
            channel=channel,
            intent=intent,
            content_len=len(content),
        )
        await self._repo.save_message_by_phone(phone, role, content, channel, intent)
        key = self._msg_key(channel, phone)
        pipe = self._redis.pipeline()
        pipe.rpush(key, json.dumps({"role": role, "content": content}))
        pipe.ltrim(key, -self.MAX_MESSAGES, -1)
        pipe.expire(key, 3600)
        await pipe.execute()

    async def build_messages(
        self,
        phone: str,
        language: str,
        new_message: str,
        product_context: str | None,
        channel: str = "text",
    ) -> list[dict]:
        summary = await self.get_summary(phone, channel)
        history = await self.get_messages(phone, channel)
        system = build_system_prompt(language, summary, product_context, channel)
        messages = [{"role": "system", "content": system}]
        messages.extend(history[-self.MAX_MESSAGES :])
        messages.append({"role": "user", "content": new_message})
        return messages

    async def generate_summary(self, phone: str, channel: str = "telegram") -> None:
        await logger.info("generate_summary_start", phone=mask_phone(phone), channel=channel)
        history = await self.get_messages(phone, channel)
        if not history:
            return
        prompt = [
            {
                "role": "system",
                "content": (
                    "Summarize this customer conversation in 2 sentences. "
                    "Include: what they asked, what they ordered if anything, their region, their name. "
                    "Reply in the same language as the conversation."
                ),
            },
            *history,
        ]
        summary = await self._openai.summarize(prompt)
        await self._repo.save_summary(phone, summary, channel)
        await self._redis.setex(self._sum_key(channel, phone), 86400, summary)
        await logger.info(
            "generate_summary_done", phone=mask_phone(phone), summary_len=len(summary)
        )
