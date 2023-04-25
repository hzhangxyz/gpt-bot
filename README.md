# gpt-bot

A GPT Command line interface bot.

This is only for gpt-3.5-turbo currently.
You need to set `OPENAI_API_KEY` in environment variable.
And maybe `OPENAI_PROXY` is also useful if you need proxy.

## Usage

`python -m gpt_bot` and enjoy.

## Command

- `/multiline`: toggle multiline input.
- `/prompt`: change [system content](https://platform.openai.com/docs/guides/chat) during chatting.
- `/rollback`: rollback the last conversation.
- `/history`: show chat history.
- `/edit`: edit what bot said just now.
- `/record`: use openai's [whister](https://platform.openai.com/docs/guides/speech-to-text) to transcribe what you are saying.
- `/quit`: quit.
