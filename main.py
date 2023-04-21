import asyncio
import fire
import openai
import os
import prompt_toolkit

# Authenticate with OpenAI API
assert "OPENAI_API_KEY" in os.environ, "OPENAI_API_KEY environment variable not set."
openai.api_key = os.environ["OPENAI_API_KEY"]
if "OPENAI_PROXY" in os.environ:
    openai.proxy = os.environ["OPENAI_PROXY"]

MODEL = "gpt-3.5-turbo"  # Choose the ID of the model to use
PROMPT = "You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible."


async def completion(chat_history, model, prompt):
    assert len(chat_history) % 2 == 1
    messages = [{"role": "system", "content": prompt}]
    roles = ["user", "assistant"]
    role_id = 0
    for msg in chat_history:
        messages.append({"role": roles[role_id], "content": msg})
        role_id = 1 - role_id
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

    chat_history = []
    session = prompt_toolkit.PromptSession()
    while True:
        user_input = await session.prompt_async(
            "You: ",
            multiline=True,
            prompt_continuation=prompt_continuation,
        )
        if user_input.startswith("/prompt "):
            prompt = user_input[8:]
            print("Update prompt to: ", prompt)
            continue

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
