FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml /app
COPY poetry.lock /app
COPY README.md /app

RUN pip install "poetry==1.8.2"
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root

COPY . /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]