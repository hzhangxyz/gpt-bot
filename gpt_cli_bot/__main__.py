import asyncio
import fire
import openai
import os
import prompt_toolkit
import tiktoken

# Authenticate with OpenAI API
assert "OPENAI_API_KEY" in os.environ, "OPENAI_API_KEY environment variable not set."
openai.api_key = os.environ["OPENAI_API_KEY"]
if "OPENAI_PROXY" in os.environ:
    openai.proxy = os.environ["OPENAI_PROXY"]

MODEL = "gpt-3.5-turbo"  # Choose the ID of the model to use
PROMPT = "You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible."
MAX_TOKENS = 4096


def num_tokens_from_messages(messages, model=MODEL):
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


async def driver(model, prompt):
    print(f"Welcome to the chatbot({model})! PROMPT is")
    print(prompt)
    print()

    multiline = False
    chat_history = []
    session = prompt_toolkit.PromptSession(history=prompt_toolkit.history.FileHistory(os.path.expanduser("~/.gpt_history")))
    while True:
        user_input = await session.prompt_async(
            "You: ",
            multiline=multiline,
            prompt_continuation=prompt_continuation,
        )
        if user_input.startswith("/multiline"):
            multiline = not multiline
            print(f"{multiline=}")
            continue
        if user_input.startswith("/prompt"):
            prompt = user_input[7:]
            print("Update prompt to: ", prompt)
            continue
        if user_input.startswith("/rollback"):
            chat_history = chat_history[:-2]
            print("Rollback the history")
            continue
        if user_input.startswith("/history"):
            print(chat_history)
            continue
        if user_input.startswith("/edit"):
            last_chat = chat_history[-1]
            user_edit = await session.prompt_async(
                "Bot: ",
                multiline=multiline,
                prompt_continuation=prompt_continuation,
                default=last_chat,
            )
            chat_history[-1] = user_edit
            continue
        if user_input.startswith("/record"):
            from .record import record_and_transcribe
            user_input = await record_and_transcribe()
            print("You:", user_input)
        if user_input.startswith("/quit"):
            break

        chat_history.append(user_input)
        print("Bot: ", end="", flush=True)
        bot_response = ""
        # Get response from OpenAI's GPT-3 model
        async for message in completion(chat_history, model, prompt):
            print(message, end="", flush=True)
            bot_response += message
        print()
        chat_history.append(bot_response)


def main(model=MODEL, prompt=PROMPT):
    asyncio.run(driver(model, prompt))


if __name__ == "__main__":
    fire.Fire(main)
