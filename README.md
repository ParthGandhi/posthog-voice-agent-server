# Posthog Meeting Copilot

https://docs.google.com/document/d/1fsxiceA97FyWSx8uWC0ulPF6cY7Biusy0dgbcHdMzlk/edit?tab=t.0

#### Linting
```
uv run ruff check . --fix
uv run mypy
```

#### For Vercel deployment
Vercel doesn't play well with `FastAPI` + `uv`, so need to freeze the deps before deploying.

```
uv pip freeze > requirements.txt
```