from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings

_conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
)

_mailer = FastMail(_conf)


async def send_password_reset_email(recipient: str, full_name: str, reset_token: str) -> None:
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background:#f4f4f4; padding:30px;">
      <div style="max-width:520px; margin:auto; background:#fff; border-radius:8px;
                  padding:32px; box-shadow:0 2px 8px rgba(0,0,0,0.1);">

        <h2 style="color:#1a1a2e; margin-bottom:8px;">Password Reset Request</h2>
        <p style="color:#555;">Hi <strong>{full_name}</strong>,</p>
        <p style="color:#555;">
          We received a request to reset your Smart Helmet System password.
          Click the button below to choose a new password.
        </p>

        <div style="text-align:center; margin:32px 0;">
          <a href="{reset_link}"
             style="background:#e63946; color:#fff; padding:14px 28px;
                    text-decoration:none; border-radius:6px; font-size:16px;
                    font-weight:bold;">
            Reset My Password
          </a>
        </div>

        <p style="color:#888; font-size:13px;">
          Or copy and paste this link into your browser:<br>
          <a href="{reset_link}" style="color:#e63946;">{reset_link}</a>
        </p>

        <hr style="border:none; border-top:1px solid #eee; margin:24px 0;">
        <p style="color:#aaa; font-size:12px;">
          This link expires in 1 hour. If you did not request a password reset,
          you can safely ignore this email.
        </p>
        <p style="color:#aaa; font-size:12px;">— Smart_Helmet</p>
      </div>
    </body>
    </html>
    """

    message = MessageSchema(
        subject="Reset Your Password — Smart_Helmet",
        recipients=[recipient],
        body=html,
        subtype=MessageType.html,
    )
    await _mailer.send_message(message)


async def send_welcome_email(recipient: str, full_name: str, reset_token: str) -> None:
    """Sent to a new supervisor/user created by an admin so they can set their password."""
    setup_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background:#f4f4f4; padding:30px;">
      <div style="max-width:520px; margin:auto; background:#fff; border-radius:8px;
                  padding:32px; box-shadow:0 2px 8px rgba(0,0,0,0.1);">

        <h2 style="color:#1a1a2e; margin-bottom:8px;">Welcome to Smart Helmet System</h2>
        <p style="color:#555;">Hi <strong>{full_name}</strong>,</p>
        <p style="color:#555;">
          Your account has been created by an administrator.
          Click the button below to set your password and access the platform.
        </p>

        <div style="text-align:center; margin:32px 0;">
          <a href="{setup_link}"
             style="background:#e63946; color:#fff; padding:14px 28px;
                    text-decoration:none; border-radius:6px; font-size:16px;
                    font-weight:bold;">
            Set My Password &amp; Access Platform
          </a>
        </div>

        <p style="color:#888; font-size:13px;">
          Or copy and paste this link into your browser:<br>
          <a href="{setup_link}" style="color:#e63946;">{setup_link}</a>
        </p>

        <hr style="border:none; border-top:1px solid #eee; margin:24px 0;">
        <p style="color:#aaa; font-size:12px;">
          This link expires in 1 hour. If you did not expect this email, please contact your administrator.
        </p>
        <p style="color:#aaa; font-size:12px;">— Smart_Helmet</p>
      </div>
    </body>
    </html>
    """

    message = MessageSchema(
        subject="Welcome to Smart Helmet — Set Your Password",
        recipients=[recipient],
        body=html,
        subtype=MessageType.html,
    )
    await _mailer.send_message(message)


async def send_worker_welcome_email(
    recipient: str,
    full_name: str,
    employee_id: str,
    helmet_code: str | None,
) -> None:
    """Sent to a new worker after a supervisor registers them."""
    helmet_line = (
        f"<p style='color:#555;'>Your assigned helmet ID is: <strong>{helmet_code}</strong></p>"
        if helmet_code
        else "<p style='color:#555;'>A helmet will be assigned to you shortly by your supervisor.</p>"
    )

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background:#f4f4f4; padding:30px;">
      <div style="max-width:520px; margin:auto; background:#fff; border-radius:8px;
                  padding:32px; box-shadow:0 2px 8px rgba(0,0,0,0.1);">

        <h2 style="color:#1a1a2e; margin-bottom:8px;">You've Been Registered as a Worker</h2>
        <p style="color:#555;">Hi <strong>{full_name}</strong>,</p>
        <p style="color:#555;">
          You have been registered in the Smart Helmet safety monitoring system.
        </p>

        <div style="background:#f8f9fa; border-radius:6px; padding:16px; margin:20px 0;">
          <p style="color:#555; margin:4px 0;">Your Employee ID: <strong>{employee_id}</strong></p>
          <p style="color:#555; margin:4px 0;">Role: <strong>Worker</strong></p>
          {helmet_line}
        </div>

        <p style="color:#555;">
          Please keep your helmet on at all times while on site. Your safety data is
          monitored in real time by the system and your supervisor.
        </p>

        <hr style="border:none; border-top:1px solid #eee; margin:24px 0;">
        <p style="color:#aaa; font-size:12px;">— Smart_Helmet Safety System</p>
      </div>
    </body>
    </html>
    """

    message = MessageSchema(
        subject="Smart Helmet — You Have Been Registered as a Worker",
        recipients=[recipient],
        body=html,
        subtype=MessageType.html,
    )
    await _mailer.send_message(message)
