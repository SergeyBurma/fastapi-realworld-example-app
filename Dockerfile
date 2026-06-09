FROM python:3.9.10-slim

ENV PYTHONUNBUFFERED 1

EXPOSE 8000
WORKDIR /app


RUN apt-get update && \
    apt-get install -y --no-install-recommends netcat python-pkg-resources && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY poetry.lock pyproject.toml ./
RUN pip install poetry setuptools && \
    poetry config virtualenvs.in-project true

RUN poetry install

COPY . ./

CMD poetry run uvicorn --host=0.0.0.0 app.main:app
