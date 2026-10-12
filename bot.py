import os
import subprocess
import ipaddress
import socket
import re
import telebot
from telebot import types
from flask import Flask, request
from google import genai
from google.genai import types as genai_types
import requests
from dotenv import load_dotenv

# ============================================
# 🔑 CONFIG (.env থেকে লোড হবে)
# ============================================
load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

AUTHORIZED_TARGETS = ["127.0.0.1", "192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)
client = genai.Client(api_key=GEMINI_API_KEY)


# ============================================
# 🛡️ TARGET VALIDATION
# ============================================
def is_authorized(target: str) -> bool:
    if target in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        target_ip = ipaddress.ip_address(target)
    except ValueError:
        try:
            target_ip = ipaddress.ip_address(socket.gethostbyname(target))
        except Exception:
            return False
    for allowed in AUTHORIZED_TARGETS:
        try:
            if "/" in allowed:
                if target_ip in ipaddress.ip_network(allowed, strict=False):
                    return True
            elif target_ip == ipaddress.ip_address(allowed):
                return True
        except ValueError:
            continue
    return False


def guard(target: str):
    if not is_authorized(target):
        return (f"🚫 UNAUTHORIZED TARGET: {target}\n\n"
                f"শুধু নিজের lab/private network এ ব্যবহার করুন।\n"
                f"Allowed: 127.0.0.1, 192.168.x.x, 10.x.x.x, 172.16-31.x.x")
    return None


# ============================================
# 🔥 REAL ATTACK TOOLS
# ============================================
def real_port_scan(target: str) -> str:
    if (err := guard(target)): return err
    try:
        r = subprocess.run(["nmap", "-sV", "-T4", "-F", target],
                          capture_output=True, text=True, timeout=60)
        return f"🔍 NMAP: {target}\n\n{r.stdout}"
    except FileNotFoundError:
        return "❌ nmap নেই। `apt install nmap`"
    except subprocess.TimeoutExpired:
        return "⏱️ Scan timeout (60s)"
    except Exception as e:
        return f"❌ Error: {e}"


def real_nikto_scan(target: str) -> str:
    if (err := guard(target)): return err
    try:
        url = target if target.startswith("http") else f"http://{target}"
        r = subprocess.run(["nikto", "-h", url, "-maxtime", "30s"],
                          capture_output=True, text=True, timeout=60)
        return f"🌐 NIKTO: {url}\n\n{r.stdout[:3000]}"
    except FileNotFoundError:
        return "❌ nikto নেই। `apt install nikto`"
    except Exception as e:
        return f"❌ Error: {e}"


def real_brute_force(target: str) -> str:
    if (err := guard(target)): return err
    try:
        ip = ipaddress.ip_address(target)
        if not ip.is_private:
            return "🚫 Brute-force শুধু private IP তে"
    except ValueError:
        return "🚫 Valid IP দিন"
    try:
        r = subprocess.run(
            ["hydra", "-l", "root", "-P", "/usr/share/wordlists/rockyou.txt",
             "-t", "4", "-f", f"ssh://{target}"],
            capture_output=True, text=True, timeout=120)
        return f"🔐 HYDRA: {target}\n\n{r.stdout[-2000:]}"
    except FileNotFoundError:
        return "❌ hydra নেই। `apt install hydra`"
    except subprocess.TimeoutExpired:
        return "⏱️ Brute-force timeout (120s)"
    except Exception as e:
        return f"❌ Error: {e}"


def real_dos_test(target: str) -> str:
    if (err := guard(target)): return err
    try:
        ip = ipaddress.ip_address(target)
        if not ip.is_private:
            return "🚫 DoS test শুধু private IP তে"
    except ValueError:
        return "🚫 Valid IP দিন"
    try:
        r = subprocess.run(
            ["timeout", "10", "hping3", "-S", "--flood", "-p", "80", target],
            capture_output=True, text=True, timeout=15)
        return f"💥 DOS TEST: {target} (10s)\n\n{r.stdout[-1000:]}"
    except FileNotFoundError:
        return "❌ hping3 নেই। `apt install hping3`"
    except Exception as e:
        return f"❌ Error: {e}"


def real_sqlmap_scan(target: str) -> str:
    if (err := guard(target)): return err
    try:
        url = target if target.startswith("http") else f"http://{target}"
        r = subprocess.run(
            ["sqlmap", "-u", f"{url}?id=1", "--batch", "--level=1", "--risk=1"],
            capture_output=True, text=True, timeout=90)
        return f"💉 SQLMAP: {url}\n\n{r.stdout[-2000:]}"
    except FileNotFoundError:
        return "❌ sqlmap নেই। `apt install sqlmap`"
    except Exception as e:
        return f"❌ Error: {e}"


def real_whois(target: str) -> str:
    try:
        r = subprocess.run(["whois", target],
                          capture_output=True, text=True, timeout=15)
        return f"📋 WHOIS: {target}\n\n{r.stdout[:2000]}"
    except FileNotFoundError:
        return "❌ whois নেই। `apt install whois`"
    except Exception as e:
        return f"❌ Error: {e}"


# ============================================
# 🎯 METASPLOIT
# ============================================
def real_metasploit(target: str, module: str = "auxiliary/scanner/portscan/tcp") -> str:
    if (err := guard(target)): return err
    try:
        msf_cmd = (f"use {module}; "
                   f"set RHOSTS {target}; "
                   f"set THREADS 10; "
                   f"run; "
                   f"exit")
        r = subprocess.run(["msfconsole", "-q", "-x", msf_cmd],
                          capture_output=True, text=True, timeout=180)
        output = r.stdout[-3000:] if r.stdout else r.stderr[-3000:]
        return f"🎯 METASPLOIT: {target}\nModule: {module}\n\n{output}"
    except FileNotFoundError:
        return "❌ metasploit নেই। `apt install metasploit-framework`"
    except subprocess.TimeoutExpired:
        return "⏱️ Metasploit timeout (180s)"
    except Exception as e:
        return f"❌ Error: {e}"


def real_msf_search(keyword: str) -> str:
    try:
        r = subprocess.run(["msfconsole", "-q", "-x", f"search {keyword}; exit"],
                          capture_output=True, text=True, timeout=60)
        return f"🔎 MSF SEARCH: {keyword}\n\n{r.stdout[-2500:]}"
    except FileNotFoundError:
        return "❌ metasploit নেই।"
    except Exception as e:
        return f"❌ Error: {e}"


# ============================================
# 📡 WIFI SCAN
# ============================================
def real_wifi_scan(interface: str = "wlan0mon", duration: int = 10) -> str:
    if not (interface.startswith("wlan") or interface.startswith("mon")):
        return "🚫 শুধু wlan* interface allowed"
    try:
        subprocess.run(
            ["timeout", str(duration), "airodump-ng", interface,
             "--output-format", "csv", "-w", "/tmp/wifiscan"],
            capture_output=True, text=True, timeout=duration + 5)
        try:
            with open("/tmp/wifiscan-01.csv", "r", errors="ignore") as f:
                content = f.read()
            return f"📡 WIFI SCAN ({interface}, {duration}s)\n\n{content[:3000]}"
        except FileNotFoundError:
            return f"📡 WIFI SCAN ({interface})\n(CSV not generated)"
    except FileNotFoundError:
        return "❌ aircrack-ng নেই। `apt install aircrack-ng`"
    except Exception as e:
        return f"❌ Error: {e}"


def real_wifi_deauth(target_bssid: str, interface: str = "wlan0mon", count: int = 5) -> str:
    if not (interface.startswith("wlan") or interface.startswith("mon")):
        return "🚫 শুধু wlan* interface allowed"
    if not re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", target_bssid):
        return "🚫 Valid MAC address দিন (AA:BB:CC:DD:EE:FF)"
    try:
        r = subprocess.run(
            ["timeout", "30", "aireplay-ng", "--deauth", str(count),
             "-a", target_bssid, interface],
            capture_output=True, text=True, timeout=35)
        return (f"📡 DEAUTH: {target_bssid}\nPackets: {count}\n\n"
                f"{r.stdout[-1500:]}\n\n⚠️ শুধু নিজের নেটওয়ার্কে!")
    except FileNotFoundError:
        return "❌ aircrack-ng নেই। `apt install aircrack-ng`"
    except Exception as e:
        return f"❌ Error: {e}"


# ============================================
# 🔍 OSINT TOOLS
# ============================================
def osint_lookup(ip_address: str) -> str:
    return f"OSINT for {ip_address}: https://shodan.io/host/{ip_address}"

def mobile_osint(number: str) -> str:
    url = f"https://myapi.lovable.app/api/public/p/pk_15d37bcead6afa3db815c6a18058a08d335e?number={number}"
    try:
        r = requests.get(url, timeout=10)
        return f"Mobile OSINT: {r.text}" if r.status_code == 200 else "Failed."
    except Exception as e:
        return f"Error: {e}"

def username_osint(username: str) -> str:
    return f"Username: {username} → https://whatsmyname.app"

def generate_defense_firewall(ip_address: str) -> str:
    return f"Block {ip_address}:\nsudo iptables -A INPUT -s {ip_address} -j DROP"


# ============================================
# 🛡️ GUARDRAIL
# ============================================
system_prompt = """
You are an Elite Ethical Hacking AI Agent.

ALLOWED TOOLS (real, only for authorized targets):
- real_port_scan (nmap)
- real_nikto_scan (nikto)
- real_brute_force (hydra) — private IP only
- real_dos_test (hping3) — private IP only
- real_sqlmap_scan (sqlmap)
- real_whois (whois)
- real_metasploit (msfconsole)
- real_msf_search (msf search)
- real_wifi_scan (airodump-ng) — own adapter only
- real_wifi_deauth (aireplay-ng) — own network only
- OSINT tools
- Defense rules

AUTHORIZED TARGETS: localhost, 192.168.x.x, 10.x.x.x, 172.16-31.x.x

PROHIBITED:
- Public IPs / company servers
- Attacking others' WiFi
- Real malware

REFUSAL: "🚫 Unauthorized target."

Help the user ethically. Always warn about legal boundaries.
"""

user_chats = {}
def get_chat_session(chat_id):
    if chat_id not in user_chats:
        user_chats[chat_id] = client.chats.create(
            model="gemini-3.5-flash-lite",
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[
                    osint_lookup, mobile_osint, username_osint,
                    generate_defense_firewall,
                    real_port_scan, real_nikto_scan, real_brute_force,
                    real_dos_test, real_sqlmap_scan, real_whois,
                    real_metasploit, real_msf_search,
                    real_wifi_scan, real_wifi_deauth,
                ],
            )
        )
    return user_chats[chat_id]


# ============================================
# 🎨 MENU
# ============================================
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🔍 Port Scan")
    btn2 = types.KeyboardButton("🌐 Web Scan")
    btn3 = types.KeyboardButton("🔐 Brute Force")
    btn4 = types.KeyboardButton("💥 DoS Test")
    btn5 = types.KeyboardButton("💉 SQLMap")
    btn6 = types.KeyboardButton("📋 WHOIS")
    btn7 = types.KeyboardButton("📱 Mobile OSINT")
    btn8 = types.KeyboardButton("👤 Username OSINT")
    btn9 = types.KeyboardButton("🛡️ Firewall Rules")
    btn10 = types.KeyboardButton("ℹ️ Help")
    btn11 = types.KeyboardButton("🎯 Metasploit")
    btn12 = types.KeyboardButton("📡 WiFi Scan")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6,
               btn7, btn8, btn9, btn10, btn11, btn12)
    return markup


# ============================================
# 📱 TELEGRAM HANDLERS
# ============================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🛡️ *Elite Ethical Hacking Agent* 🛡️\n\n"
        "আমি একটি AI-চালিত সিকিউরিটি অ্যাসিস্ট্যান্ট।\n\n"
        "⚠️ *Allowed Targets:*\n"
        "• localhost / 127.0.0.1\n"
        "• 192.168.x.x\n"
        "• 10.x.x.x\n"
        "• 172.16-31.x.x\n\n"
        "📋 *Available Tools:*\n"
        "1. 🔍 Port Scan (nmap)\n"
        "2. 🌐 Web Scan (nikto)\n"
        "3. 🔐 Brute Force (hydra)\n"
        "4. 💥 DoS Test (hping3)\n"
        "5. 💉 SQLMap\n"
        "6. 📋 WHOIS\n"
        "7. 📱 Mobile OSINT\n"
        "8. 👤 Username OSINT\n"
        "9. 🛡️ Firewall Rules\n"
        "10. 🎯 Metasploit\n"
        "11. 📡 WiFi Scan\n\n"
        "👇 মেনু থেকে বেছে নিন বা লিখুন:\n"
        "`scan 192.168.1.1`"
    )
    bot.send_message(message.chat.id, welcome_text,
                     parse_mode="Markdown", reply_markup=main_menu())


@bot.message_handler(commands=['menu'])
def show_menu(message):
    bot.send_message(message.chat.id, "📋 *Main Menu*",
                     parse_mode="Markdown", reply_markup=main_menu())


@bot.message_handler(commands=['help'])
def show_help(message):
    help_text = (
        "📖 *Help — Command Reference*\n\n"
        "*🔍 Port Scan:* `scan 192.168.1.1`\n"
        "*🌐 Web Scan:* `nikto 192.168.1.1`\n"
        "*🔐 Brute Force:* `brute force 192.168.1.5`\n"
        "*💥 DoS Test:* `dos test 192.168.1.5`\n"
        "*💉 SQLMap:* `sqlmap 192.168.1.5`\n"
        "*📋 WHOIS:* `whois example.com`\n"
        "*📱 Mobile OSINT:* `mobile osint 01712345678`\n"
        "*👤 Username OSINT:* `username osint john_doe`\n"
        "*🛡️ Firewall:* `block 1.2.3.4`\n"
        "*🎯 Metasploit:* `metasploit 192.168.1.5`\n"
        "                `msf search vsftpd`\n"
        "*📡 WiFi Scan:* `wifi scan wlan0mon`\n"
        "              `wifi deauth AA:BB:CC:DD:EE:FF wlan0mon`\n\n"
        "⚠️ *শুধু নিজের lab/private network এ!*"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")


# --- Button handlers ---
@bot.message_handler(func=lambda m: m.text == "🔍 Port Scan")
def btn_portscan(message):
    bot.reply_to(message, "🔍 *Port Scan*\n\n`scan 192.168.1.1`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🌐 Web Scan")
def btn_webscan(message):
    bot.reply_to(message, "🌐 *Web Scan*\n\n`nikto 192.168.1.1`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔐 Brute Force")
def btn_brute(message):
    bot.reply_to(message, "🔐 *Brute Force*\n\n`brute force 192.168.1.5`\n⚠️ private IP only", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💥 DoS Test")
def btn_dos(message):
    bot.reply_to(message, "💥 *DoS Test*\n\n`dos test 192.168.1.5`\n⚠️ private IP only", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💉 SQLMap")
def btn_sqlmap(message):
    bot.reply_to(message, "💉 *SQLMap*\n\n`sqlmap 192.168.1.5`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📋 WHOIS")
def btn_whois(message):
    bot.reply_to(message, "📋 *WHOIS*\n\n`whois example.com`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📱 Mobile OSINT")
def btn_mobile(message):
    bot.reply_to(message, "📱 *Mobile OSINT*\n\n`mobile osint 01712345678`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 Username OSINT")
def btn_user(message):
    bot.reply_to(message, "👤 *Username OSINT*\n\n`username osint john_doe`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🛡️ Firewall Rules")
def btn_fw(message):
    bot.reply_to(message, "🛡️ *Firewall*\n\n`block 1.2.3.4`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "ℹ️ Help")
def btn_help(message):
    show_help(message)

@bot.message_handler(func=lambda m: m.text == "🎯 Metasploit")
def btn_msf(message):
    bot.reply_to(message,
        "🎯 *Metasploit*\n\n"
        "`metasploit 192.168.1.5`\n"
        "`msf search vsftpd`\n\n"
        "⚠️ Render-এ কাজ নাও করতে পারে",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📡 WiFi Scan")
def btn_wifi(message):
    bot.reply_to(message,
        "📡 *WiFi Scan*\n\n"
        "`wifi scan wlan0mon`\n"
        "`wifi deauth AA:BB:CC:DD:EE:FF wlan0mon`\n\n"
        "⚠️ Render-এ WiFi নেই — local Kali-তে চালান",
        parse_mode="Markdown")


# ============================================
# 📨 MESSAGE HANDLER (AI)
# ============================================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    try:
        chat = get_chat_session(message.chat.id)
        response = chat.send_message(message.text)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {e}")


# ============================================
# 🌐 WEBHOOK (Render এর জন্য)
# ============================================
@app.route('/' + TELEGRAM_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(
        request.stream.read().decode("utf-8"))])
    return "!", 200

@app.route("/")
def home():
    return "🛡️ Bot running!", 200


# ============================================
# 🚀 MAIN — Local vs Render
# ============================================
if __name__ == "__main__":
    if os.environ.get("RENDER"):
        # Render এ webhook mode
        print("🛡️ Bot webhook mode এ চলছে (Render)...")
        app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
    else:
        # Local এ polling mode
        bot.remove_webhook()
        print("🛡️ Bot polling mode এ চলছে (Local)...")
        print("Telegram এ /start পাঠান")
        bot.infinity_polling()