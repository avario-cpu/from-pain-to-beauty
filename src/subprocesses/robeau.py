import asyncio

TARGET_SENTENCE = "Hello, how can I help you?"


async def match_target(queue: asyncio.Queue):
    while True:
        transcript = await queue.get()
        if TARGET_SENTENCE in transcript:
            print(f"Matched target sentence: {transcript}")
        else:
            print(f"Did not match: {transcript}")
        queue.task_done()


if __name__ == "__main__":
    from google_stt import transcriptions_queue
    asyncio.run(match_target(transcriptions_queue))
