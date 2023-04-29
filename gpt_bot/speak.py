import aiohttp
import asyncio
import pyaudio
import tempfile
import wave

CHUNK = 1024


def url_and_param_tts():
    url = "https://tts.baidu.com/text2audio"
    params = {
        "cuid": "me",
        "ctp": 1,
        "lan": "zh",
        "aue": 6,
        "pdt": 301,
        "spd": 15,
    }
    return url, params


def url_and_param_tsn():
    url = "https://tsn.baidu.com/text2audio"
    params = {
        "tok": ACCESS_TOKEN,
        "cuid": "me",
        "ctp": 1,
        "lan": "zh",
        "aue": 6,
        "per": 3,
        "spd": 15,
    }
    return url, params


class StreamContext:

    def __init__(self, device, wave_file, *args, **kwargs):
        self.device = device
        self.wave_file = wave_file
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        self.stream = self.device.open(*self.args, **self.kwargs)
        return self

    def __exit__(self, *args):
        self.stream.close()

    def keep_play(self):
        while True:
            data = self.wave_file.readframes(CHUNK)
            self.stream.write(data)
            if len(data) == 0:
                break


class Player:

    def __init__(self):
        self.device = pyaudio.PyAudio()

    def __call__(self, *args, **kwargs):
        return StreamContext(self.device, *args, **kwargs)


player = Player()


async def speak(text):
    url, params = url_and_param_tts()

    params["tex"] = text

    with tempfile.NamedTemporaryFile(suffix=".wav") as audio_file:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=params) as response:
                audio_data = await response.read()
                audio_file.write(audio_data)

        audio_file.file.seek(0)

        with wave.open(audio_file, "rb") as file:
            with player(
                    file,
                    format=player.device.get_format_from_width(file.getsampwidth()),
                    channels=file.getnchannels(),
                    rate=file.getframerate(),
                    output=True,
            ) as stream:

                await asyncio.to_thread(stream.keep_play)
