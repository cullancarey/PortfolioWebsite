import logging
import json
import os
import base64
import boto3
import urllib3
from urllib.parse import unquote

logger = logging.getLogger()
logger.setLevel(logging.INFO)

http = urllib3.PoolManager()


def lambda_handler(event, context):
    logger.info(f"Event received: {json.dumps(event)}")

    try:
        if event.get("isBase64Encoded"):
            body = decode_body_to_dict(event["body"])
        else:
            body = json.loads(event["body"])
    except Exception as e:
        logger.error(f"Error parsing body: {e}")
        return error_response("Invalid request payload.", 400)

    logger.info(f"Decoded body: {body}")

    if body.get("BotCheck"):
        logger.info("Honeypot triggered. Bot detected.")
        return success_response("Thanks, bot detected. Submission ignored.")

    captcha_token = body.get("g-recaptcha-response")
    if not captcha_token:
        return error_response("Captcha missing.", 400)

    source_ip = (
        event.get("requestContext", {}).get("http", {}).get("sourceIp", "Unknown")
    )
    captcha_valid = verify_captcha(captcha_token, source_ip)

    if not captcha_valid:
        return error_response("Captcha verification failed.", 403)

    customer_email = body.get("CustomerEmail")
    customer_message = body.get("MessageDetails")

    if not (customer_email and customer_message):
        return error_response("Missing required fields.", 400)

    try:
        send_email(customer_email, customer_message)
        logger.info("Email sent successfully.")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return error_response("Error sending message. Please try again later.", 500)

    return success_response(
        "Thank you for your message! Cullan will get back to you shortly!"
    )


def decode_body_to_dict(encoded_body):
    decoded = base64.b64decode(encoded_body.encode("utf-8")).decode("utf-8")
    return {
        key: unquote(value.replace("+", " "))
        for key, value in (
            item.split("=", 1) for item in decoded.split("&") if "=" in item
        )
    }


def verify_captcha(captcha_response, source_ip):
    captcha_secret = get_captcha_secret()
    response = http.request(
        "POST",
        "https://www.google.com/recaptcha/api/siteverify",
        fields={
            "secret": captcha_secret,
            "response": captcha_response,
            "remoteip": source_ip,
        },
    )
    result = json.loads(response.data.decode("utf-8"))
    logger.info(f"Captcha verification result: {result}")
    return result.get("success", False)


def get_captcha_secret():
    ssm = boto3.client("ssm")
    response = ssm.get_parameter(
        Name=f"{os.environ['environment']}_google_captcha_secret",
        WithDecryption=True,
    )
    return response["Parameter"]["Value"]


def send_email(customer_email, customer_message):
    ses = boto3.client("ses")
    domain = os.environ["website"].replace("form.", "")
    subject = f"Inquiry from {domain}"
    text_body = f'Hi Cullan!\n\nYou\'ve received a message from {customer_email}:\n\n"{customer_message}"\n\nReply directly to this email.'
    html_body = f"""\
    <html><body>
    <p>Hi Cullan!<br><br>You've received a message from <strong>{customer_email}</strong>:<br><br>"{customer_message}"<br><br>Reply directly to this email.</p>
    </body></html>"""

    ses.send_email(
        Source=f"noreply@{domain}",
        Destination={"ToAddresses": ["cullan@cullancarey.com"]},
        Message={
            "Subject": {"Data": subject},
            "Body": {
                "Text": {"Data": text_body},
                "Html": {"Data": html_body},
            },
        },
        ReplyToAddresses=[customer_email],
    )


def response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body_dict),
    }


def success_response(message):
    return response(200, {"message": message})


def error_response(message, status_code):
    return response(status_code, {"error": message})
