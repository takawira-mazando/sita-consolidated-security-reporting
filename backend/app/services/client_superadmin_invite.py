from html import escape
import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings
from app.monitoring.egress import check


class InvitationEmailConfigurationError(RuntimeError):
    pass


class InvitationEmailDeliveryError(RuntimeError):
    pass


def send_client_superadmin_invite(
    *,
    email: str,
    client_name: str,
    setup_url: str,
    expires_in_hours: int,
) -> None:
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        raise InvitationEmailConfigurationError(
            "Configure SMTP_HOST, SMTP_USER, and SMTP_PASSWORD to send client invitations."
        )
    if (
        settings.environment.lower() not in {"dev", "development", "test", "testing"}
        and not settings.frontend_base_url.startswith("https://")
    ):
        raise InvitationEmailConfigurationError(
            "FRONTEND_BASE_URL must use HTTPS outside development."
        )

    safe_client_name = " ".join(client_name.replace("\r", " ").replace("\n", " ").split())
    message = EmailMessage()
    message["Subject"] = f"Set up your {safe_client_name} superadmin account"
    message["From"] = settings.smtp_user
    message["To"] = email
    message.set_content(
        f"You have been selected as the superadmin for {safe_client_name}.\n\n"
        f"Use this one-time link to set your password: {setup_url}\n\n"
        f"The link expires in {expires_in_hours} hours. If you did not expect this "
        "invitation, you can ignore this email."
    )
    message.add_alternative(
        "<p>You have been selected as the superadmin for "
        f"<strong>{escape(safe_client_name)}</strong>.</p>"
        f'<p><a href="{setup_url}">Set your password</a></p>'
        f"<p>This one-time link expires in {expires_in_hours} hours. "
        "If you did not expect this invitation, you can ignore this email.</p>",
        subtype="html",
    )

    try:
        check("client_superadmin_invite_smtp")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException, RuntimeError) as exc:
        if isinstance(exc, InvitationEmailConfigurationError):
            raise
        raise InvitationEmailDeliveryError(
            "The superadmin invitation email could not be delivered."
        ) from exc


def send_client_superadmin_credentials(
    *,
    email: str,
    client_name: str,
    temporary_password: str,
) -> None:
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        raise InvitationEmailConfigurationError(
            "Configure SMTP_HOST, SMTP_USER, and SMTP_PASSWORD to send client credentials."
        )

    safe_client_name = " ".join(client_name.replace("\r", " ").replace("\n", " ").split())
    message = EmailMessage()
    message["Subject"] = f"Your {safe_client_name} superadmin account"
    message["From"] = settings.smtp_user
    message["To"] = email
    message.set_content(
        f"Your superadmin account for {safe_client_name} has been created.\n\n"
        f"Email: {email}\n"
        f"Temporary password: {temporary_password}\n\n"
        "Change this password after your first sign-in."
    )
    message.add_alternative(
        "<p>Your superadmin account for "
        f"<strong>{escape(safe_client_name)}</strong> has been created.</p>"
        f"<p>Email: <strong>{escape(email)}</strong></p>"
        f"<p>Temporary password: <code>{escape(temporary_password)}</code></p>"
        "<p>Change this password after your first sign-in.</p>",
        subtype="html",
    )

    try:
        check("client_superadmin_credentials_smtp")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException, RuntimeError) as exc:
        raise InvitationEmailDeliveryError(
            "The superadmin credentials email could not be delivered."
        ) from exc
