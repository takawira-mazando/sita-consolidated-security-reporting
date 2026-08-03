import smtplib
from email.mime.text import MIMEText
from jinja2 import Template
from app.config import settings

EMAIL_TEMPLATE = Template("""
<h2>SITA Alert: {{ alert.title }}</h2>
<p><strong>Severity:</strong> {{ alert.severity }}</p>
<p><strong>Source:</strong> {{ alert.source }}</p>
<p><strong>Rule:</strong> {{ alert.rule_id }}</p>
<p>{{ alert.description }}</p>
<hr>
<p><small>SITA Security Intelligence Platform</small></p>
""")

class EmailAdapter:
    def __init__(self):
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password

    def send(self, alert: dict) -> bool:
        try:
            msg = MIMEText(EMAIL_TEMPLATE.render(alert=alert), "html")
            msg["Subject"] = f"[SITA {alert.get('severity','').upper()}] {alert.get('title','')}"
            msg["From"] = self.user
            msg["To"] = "soc@sita.com"

            with smtplib.SMTP(self.host, self.port) as server:
                if self.user:
                    server.starttls()
                    server.login(self.user, self.password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Email dispatch failed: {e}")
            return False
