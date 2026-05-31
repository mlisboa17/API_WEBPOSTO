from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
from typing import AsyncIterator

router = APIRouter()
_job_queues: dict[str, asyncio.Queue[str]] = {}


async def event_generator() -> AsyncIterator[str]:
    # very small example heartbeat + metrics streamer
    i = 0
    while True:
        payload = {"type": "tick", "i": i}
        yield f"data: {json.dumps(payload)}\n\n"
        i += 1
        await asyncio.sleep(0.5)


def get_job_queue(job_id: str) -> asyncio.Queue[str]:
    queue = _job_queues.get(job_id)
    if queue is None:
        queue = asyncio.Queue()
        _job_queues[job_id] = queue
    return queue


async def publish_job_event(job_id: str, payload: dict) -> None:
    queue = get_job_queue(job_id)
    await queue.put(f"data: {json.dumps(payload, default=str)}\n\n")


async def job_event_generator(job_id: str) -> AsyncIterator[str]:
    queue = get_job_queue(job_id)
    while True:
        event = await queue.get()
        yield event
        if '"event":"done"' in event or '"event": "done"' in event:
            break


@router.get("/api/stream")
async def stream(request: Request):
    async def streamer():
        async for event in event_generator():
            if await request.is_disconnected():
                break
            yield event

    return StreamingResponse(streamer(), media_type="text/event-stream")


@router.get("/api/adelaide/stream/{job_id}")
async def adelaide_stream(job_id: str, request: Request):
    async def streamer():
        async for event in job_event_generator(job_id):
            if await request.is_disconnected():
                break
            yield event

    return StreamingResponse(streamer(), media_type="text/event-stream")
