import asyncio
from typing import NamedTuple

from kosong.base.message import ContentPart, ToolCall, ToolCallPart
from kosong.tooling import ToolResult

from kimi_cli.logging import logger


class RunBegin:
    pass


class RunEnd:
    pass


class StepBegin(NamedTuple):
    n: int


class StepInterrupted:
    pass


class ContextUsageUpdate(NamedTuple):
    usage_percentage: float


type ControlFlowEvent = RunBegin | RunEnd | StepBegin | StepInterrupted | ContextUsageUpdate
type Event = ControlFlowEvent | ContentPart | ToolCall | ToolCallPart | ToolResult


class EventQueue:
    def __init__(self):
        self._queue = asyncio.Queue()

    def put_nowait(self, event: Event):
        logger.debug("Emitting event: {event}", event=event)
        self._queue.put_nowait(event)

    async def get(self) -> Event:
        event = await self._queue.get()
        logger.debug("Consuming event: {event}", event=event)
        return event
