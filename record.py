import asyncio
import numpy
import openai
import pyaudio
import tempfile
import threading
import wave

#设置参数
CHUNK = 1024  #每次读取的buffer 大小
FORMAT = pyaudio.paInt16
CHANNELS = 1  #单通道
RATE = 16 * 1024  #采样率


class StreamContext:

    def __init__(self, device, *args, **kwargs):
        self.device = device
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        self.stream = self.device.open(*self.args, **self.kwargs)
        self.frames = []
        self.keep_running = True
        return self

    def __exit__(self, *args):
        self.stream.stop_stream()
        self.stream.close()

    def keep_record(self):
        while self.keep_running:
            data = self.stream.read(CHUNK)
            self.frames.append(numpy.frombuffer(data, dtype=numpy.int16))


class Recorder:

    def __init__(self):
        self.device = pyaudio.PyAudio()

    def __call__(self, *args, **kwargs):
        return StreamContext(self.device, *args, **kwargs)


recorder = Recorder()


async def record():
    with recorder(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK) as stream:
        print("recording... press enter to stop ", end="")

        t = threading.Thread(target=stream.keep_record)
        t.start()

        input_event = asyncio.Event()
        asyncio.get_event_loop().add_reader(0, input_event.set)
        await input_event.wait()
        input()

        stream.keep_running = False
        t.join()

        audio_data = numpy.concatenate(stream.frames, axis=0)
        return audio_data


async def transcribe(audio_data):
    with tempfile.NamedTemporaryFile(suffix=".wav") as audio_file:
        print("transcribing... ", end="")

        with wave.open(audio_file, "wb") as wavfile:
            wavfile.setnchannels(1)  # 设置声道数为1
            wavfile.setsampwidth(2)  # 设置采样位数为16位
            wavfile.setframerate(RATE)  # 设置采样率为RATE
            wavfile.writeframes(audio_data.tobytes())  # 将数据写入wav文件

        audio_file.file.seek(0)
        transcript = await openai.Audio.atranscribe("whisper-1", audio_file)

        print()
        return transcript.text


async def record_and_transcribe():
    return await transcribe(await record())
