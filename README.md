
#### Linting
```
uv run ruff check . --fix
uv run mypy
```

#### For Vercel deployment
```
uv pip freeze > requirements.txt
```