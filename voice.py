import os
import asyncio
import traceback

import pyaudio

import argparse

from google import genai
from google.genai import types

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
os.environ["GEMINI_API_KEY"] = "AIzaSyA04SDintKYC9tOBD_1u20x_YAK2pAR_qQ"

MODEL = "models/gemini-2.0-flash-live-001"

client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)

CONFIG = types.LiveConnectConfig(
    response_modalities=["audio"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
        )
    ),
    system_instruction=types.Content(
        parts=[types.Part.from_text(text="you are an event management expert you have to help the user plan their dream event.")],
        role="user"
    ),
)

pya = pyaudio.PyAudio()

class AudioLoop:
    def __init__(self):
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self.send_text_task = None
        self.receive_audio_task = None
        self.play_audio_task = None

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(
                input,
                "message > ",
            )
            if text.lower() == "q":
                break
            await self.session.send(input=text or ".", end_of_turn=True)

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg)

    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

    async def receive_audio(self):
        while True:
            turn = self.session.receive()
            async for response in turn:
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
                    continue
                if text := response.text:
                    print(text, end="")

            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)

    async def run(self):
        try:
            async with (
                client.aio.live.connect(model=MODEL, config=CONFIG) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session

                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)

                send_text_task = tg.create_task(self.send_text())
                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())
                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())

                await send_text_task
                raise asyncio.CancelledError("User requested exit")

        except asyncio.CancelledError:
            pass
        except ExceptionGroup as EG:
            self.audio_stream.close()
            traceback.print_exception(EG)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    main = AudioLoop()
    asyncio.run(main.run())