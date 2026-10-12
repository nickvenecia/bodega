"""AI helpers: connect any provider with your own API key, then let it tidy names, find links and prices.

providers.py  the providers (Anthropic, OpenAI, Gemini, Kimi, OpenRouter… or any OpenAI-compatible one),
              their live model lists, and one way to ask a question
tasks.py      the jobs: update from links, find missing links, tidy names, answer a question about your gear

Nothing an AI suggests changes your gear until you approve it (the Review window in the app).
"""
