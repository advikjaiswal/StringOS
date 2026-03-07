def send_email(to, subject, body):
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "your_email@gmail.com"
    msg["To"] = to

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login("your_email@gmail.com", "your-password-or-app-password")
        server.send_message(msg)

    return {"status": "success", "message": f"Email sent to {to}"} 