RUN echo "deb http://deb.debian.org/debian trixie main non-free" > /etc/apt/sources.list.d/non-free.list \
    && apt-get update && apt-get install -y \
    nmap \
    hydra \
    nikto \
    sqlmap \
    hping3 \
    whois \
    aircrack-ng \
    net-tools \
    wireless-tools \
    && rm -rf /var/lib/apt/lists/*