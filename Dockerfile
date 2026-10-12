FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    nmap \
    hydra \
    sqlmap \
    hping3 \
    whois \
    aircrack-ng \
    net-tools \
    wireless-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]