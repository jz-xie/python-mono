FROM python:3.9-slim


WORKDIR /app/

# Install SSH agent
RUN apt update && apt install openssh-server -y
RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan bitbucket.org >> ~/.ssh/known_hosts

# Install Poetry
RUN python -m pip install poetry==1.4.1
RUN poetry config virtualenvs.create false --local

COPY . .
RUN --mount=type=ssh poetry install
# docker buildx build --ssh default=<ssh_key_path>