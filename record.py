import numpy
import torch
import whisper
import pyaudio
import threading

#设置参数
CHUNK = 1024  #每次读取的buffer 大小
FORMAT = pyaudio.paFloat32
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
            self.frames.append(numpy.frombuffer(data, dtype=numpy.float32))


class Recorder:

    def __init__(self):
        self.device = pyaudio.PyAudio()

    def __call__(self, *args, **kwargs):
        return StreamContext(self.device, *args, **kwargs)


recorder = Recorder()


def record():
    with recorder(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK) as stream:
        print("recording... press enter to stop", end="")

        t = threading.Thread(target=stream.keep_record)
        t.start()
        input()
        stream.keep_running = False
        t.join()

        audio_data = numpy.concatenate(stream.frames, axis=0).astype(numpy.float32)
        return audio_data


model = whisper.load_model("tiny")


def transcribe(audio_data):
    print("transcribing...", end="")
    result = whisper.transcribe(model, audio_data, fp16=False)
    print()
    return result["text"]


def record_and_transcribe():
    return transcribe(record())
