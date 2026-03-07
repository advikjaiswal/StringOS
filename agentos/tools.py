# tools.py
import requests
from bs4 import BeautifulSoup
import os
import subprocess
import smtplib
from email.message import EmailMessage

# Simple web scraper
def web_scraper(url):
    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        return '\n'.join([a.text.strip() for a in soup.find_all('a') if a.text.strip()])
    except Exception as e:
        return f"Web scraping failed: {str(e)}"

# File writer utility
def file_writer(filename, content):
    try:
        with open(filename, 'w') as f:
            f.write(content)
        return f"✅ File '{filename}' written successfully."
    except Exception as e:
        return f"❌ File writing failed: {str(e)}"

# Email sender utility
def email_sender(to, subject, content):
    try:
        msg = EmailMessage()
        msg.set_content(content)
        msg['Subject'] = subject
        msg['From'] = 'you@example.com'  # Change to real sender
        msg['To'] = to

        with smtplib.SMTP('localhost') as server:
            server.send_message(msg)
        return f"📧 Email sent to {to}"
    except Exception as e:
        return f"❌ Email sending failed: {str(e)}"

# Summarization placeholder
def summarizer(text):
    return text[:500] + ('...' if len(text) > 500 else '')

# Bash command runner
def bash_runner(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True)
        return result.stdout.decode('utf-8') or result.stderr.decode('utf-8')
    except Exception as e:
        return f"❌ Bash command failed: {str(e)}"
