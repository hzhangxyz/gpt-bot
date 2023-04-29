import asyncio
import openai
import os
import prompt_toolkit
import tiktoken

# Some static configuration
MODEL = "gpt-3.5-turbo"  # Choose the ID of the model to use
PROMPT = "You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible."
MAX_TOKENS = 4096

# Authenticate with OpenAI API
assert "OPENAI_API_KEY" in os.environ, "OPENAI_API_KEY environment variable not set."
openai.api_key = os.environ["OPENAI_API_KEY"]
if "OPENAI_PROXY" in os.environ:
    openai.proxy = os.environ["OPENAI_PROXY"]


def num_tokens_from_messages(messages, model):
    encoding = tiktoken.encoding_for_model(model)
    if model == MODEL:  # note: future models may deviate from this
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens
    else:
        raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.
  See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")


def generate_messages(chat_history, model, prompt):
    assert len(chat_history) % 2 == 1
    messages = [{"role": "system", "content": prompt}]
    roles = ["user", "assistant"]
    role_id = 0
    for msg in chat_history:
        messages.append({"role": roles[role_id], "content": msg})
        role_id = 1 - role_id
    while num_tokens_from_messages(messages, model) > MAX_TOKENS // 2:
        messages = [messages[0]] + messages[3:]
    return messages


async def completion(chat_history, model, prompt):
    messages = generate_messages(chat_history, model, prompt)
    stream = await openai.ChatCompletion.acreate(model=model, messages=messages, stream=True)
    async for response in stream:
        obj = response['choices'][0]
        if obj['finish_reason'] is not None:
            assert not obj['delta']
            if obj['finish_reason'] == 'length':
                yield ' [!Output truncated due to limit]'
            return
        if 'role' in obj['delta']:
            if obj['delta']['role'] != 'assistant':
                raise ValueError("Role error")
        if 'content' in obj['delta']:
            yield obj['delta']['content']


def prompt_continuation(width, line_number, is_soft_wrap):
    return '.' * (width - 1) + ' '


class App:

    def __init__(self, model=MODEL, prompt=PROMPT, history="~/.gpt_history"):
        self.model = model
        self.prompt = prompt

        self.middleware = {}

        self.multiline = False
        self.chat_history = []
        self.session = prompt_toolkit.PromptSession(history=prompt_toolkit.history.FileHistory(os.path.expanduser(history)))
        self.speak = False

    async def driver(self):
        print(f"Welcome to the chatbot({self.model})! PROMPT is")
        print(self.prompt)
        print()

        while True:
            user_input = await self.session.prompt_async(
                "You: ",
                multiline=self.multiline,
                prompt_continuation=prompt_continuation,
            )

            do_quit = False
            do_continue = False
            for prefix, function in self.middleware.items():
                if user_input.startswith(prefix):
                    try:
                        line = user_input[len(prefix):]
                        if asyncio.iscoroutinefunction(function):
                            user_input = await function(self, line)
                        else:
                            user_input = function(self, line)
                        break
                    except self.Exit:
                        do_quit = True
                        break
                    except self.Continue:
                        do_continue = True
                        break
            if do_quit:
                break
            if do_continue:
                continue

            self.chat_history.append(user_input)
            print("Bot: ", end="", flush=True)
            bot_response = ""
            # Get response from OpenAI's GPT-3 model
            async for message in completion(self.chat_history, self.model, self.prompt):
                print(message, end="", flush=True)
                bot_response += message
            print()
            if self.speak:
                from .speak import speak
                await speak(bot_response)
            self.chat_history.append(bot_response)

    def handle(self, prefix):

        def handle_for_prefix(function):
            self.middleware[prefix] = function
            return function

        return handle_for_prefix

    class Exit(BaseException):
        pass

    class Continue(BaseException):
        pass


app = App()


@app.handle("/quit")
@app.handle("/exit")
def _(self, line):
    raise self.Exit()


@app.handle("/multiline")
def _(self, line):
    self.multiline = not self.multiline
    print(f"{self.multiline=}")
    raise self.Continue()


@app.handle("/prompt")
def _(self, line):
    self.prompt = line
    print("Update prompt to:", self.prompt)
    raise self.Continue()


@app.handle("/record")
async def _(self, line):
    from .record import record_and_transcribe
    user_input = await record_and_transcribe()
    print("You:", user_input)
    return user_input


@app.handle("/history")
def _(self, line):
    print("History:")
    print("Sys:", self.prompt)
    for i, content in enumerate(self.chat_history):
        print("You:" if i % 2 == 0 else "Bot:", content)
    raise self.Continue()


@app.handle("/rollback")
def _(self, line):
    self.chat_history = self.chat_history[:-2]
    print("Rollback the history")
    raise self.Continue()


@app.handle("/edit")
async def _(self, line):
    last_chat = self.chat_history[-1]
    user_edit = await self.session.prompt_async(
        "Bot: ",
        multiline=self.multiline,
        prompt_continuation=prompt_continuation,
        default=last_chat,
    )
    self.chat_history[-1] = user_edit
    raise self.Continue()


@app.handle("/speak")
def _(self, line):
    self.speak = not self.speak
    print(f"{self.speak=}")
    raise self.Continue()


if __name__ == "__main__":
    asyncio.run(app.driver())
