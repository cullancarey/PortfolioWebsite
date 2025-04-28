"""Lambda to send intake form emails after captcha verification."""

import logging
import json
import os
import base64
from urllib.parse import unquote
import boto3
import urllib3

# Global clients to speed up cold starts
ses_client = boto3.client("ses")
ssm_client = boto3.client("ssm")
http = urllib3.PoolManager()

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Main Lambda handler."""
    logger.info(f"Event received: {json.dumps(event)}")

    try:
        string_dict = parse_event_body(event)
    except Exception as e:
        logger.error(f"Failed to parse event body: {e}")
        return error_response(400, "Invalid request payload.")

    if string_dict.get("BotCheck"):
        logger.warning("Bot detected by honeypot field.")
        return success_response("Nice try, bot.")

    captcha_response = string_dict.get("g-recaptcha-response")
    customer_email = string_dict.get("CustomerEmail", "")
    customer_message = string_dict.get("MessageDetails", "")

    if not captcha_response:
        logger.error("Missing captcha token.")
        return error_response(400, "Captcha verification failed.")

    source_ip = (
        event.get("requestContext", {}).get("http", {}).get("sourceIp", "Unknown")
    )
    captcha_success = verify_captcha(captcha_response, source_ip)

    if not captcha_success:
        logger.warning("Captcha verification failed.")
        return error_response(403, "Captcha verification failed.")

    if not validate_email(customer_email):
        logger.error(f"Invalid email provided: {customer_email}")
        return error_response(400, "Invalid email address.")

    send_email(customer_email, customer_message)
    logger.info("Email sent successfully.")
    return success_response(
        "Thank you for your message! I will get back to you shortly."
    )


def parse_event_body(event):
    """Decode event body."""
    body = event.get("body", "")
    if event.get("isBase64Encoded", False):
        body = base64.b64decode(body).decode("utf-8")

    # Try JSON first, fallback to form-url-encoded
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        logger.info("Falling back to URL-decoded body parsing.")
        return {
            key: unquote(value.replace("+", " "))
            for key, value in (
                map(str.strip, item.split("=", 1))
                for item in body.split("&")
                if "=" in item
            )
        }


def verify_captcha(captcha_response, source_ip):
    """Verify captcha with Google."""
    secret = get_captcha_secret()
    resp = http.request(
        "POST",
        "https://www.google.com/recaptcha/api/siteverify",
        fields={
            "secret": secret,
            "response": captcha_response,
            "remoteip": source_ip,
        },
    )
    result = json.loads(resp.data.decode("utf-8"))
    success = result.get("success", False)
    if not success:
        logger.error(f"Captcha verification failed: {result.get('error-codes')}")
    return success


def send_email(customer_email, customer_message):
    """Send an email via AWS SES."""
    domain = os.environ["website"].replace("form.", "")
    source_email = f"noreply@{domain}"
    subject = f"Inquiry from {domain}"
    body_text = f"""Hi Cullan!

You've received a message from {customer_email}:
"{customer_message}"

You can reply directly to this email."""

    body_html = f"""<html>
<body>
<p>Hi Cullan!<br>
You've received a message from <strong>{customer_email}</strong>.<br>
Message: "{customer_message}".<br>
Just hit reply to respond!</p>
</body>
</html>"""

    ses_client.send_email(
        Source=source_email,
        Destination={"ToAddresses": ["cullan@cullancarey.com"]},
        Message={
            "Subject": {"Data": subject},
            "Body": {
                "Text": {"Data": body_text},
                "Html": {"Data": body_html},
            },
        },
        ReplyToAddresses=[customer_email],
    )


def get_captcha_secret():
    """Retrieve captcha secret from SSM Parameter Store."""
    param_name = f"{os.environ['environment']}_google_captcha_secret"
    response = ssm_client.get_parameter(Name=param_name, WithDecryption=True)
    return response["Parameter"]["Value"]


def validate_email(email):
    """Very basic email validation."""
    return "@" in email and "." in email


def success_response(message):
    """Helper for 200 responses."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message}),
    }


def error_response(status_code, message):
    """Helper for error responses."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
