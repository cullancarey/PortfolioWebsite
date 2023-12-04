"""Lambda to send intake form emails"""
import logging
import json
import os
import base64
import sys
from urllib.parse import unquote
import boto3
import urllib3

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Main lambda function for execution"""
    logger.info(f"Event received: {json.dumps(event)}")
    if event["isBase64Encoded"]:
        try:
            string_dict = decode_body_to_dict(event["body"])
        except KeyError as error:
            logger.error(f"Error find key 'body': {error}")
            sys.exit()
        else:
            logger.info(f"Decoded body to dictionary: {string_dict}")
    else:
        string_dict = json.loads(event["body"])
        logger.info(string_dict)

    # Catch bots
    if string_dict.get("BotCheck", False):
        logger.info("Honeypot field filled out, bot detected.")
        return html_response("Ha! Found ya! Get lost, bot.")

    source_ip = event["requestContext"]["http"]["sourceIp"]
    captcha = string_dict["g-recaptcha-response"]
    captcha_success, server_response = verify_captcha(captcha, source_ip)

    customer_email = string_dict.get("CustomerEmail", "")
    customer_message = string_dict.get("MessageDetails", "")
    if captcha_success:
        logger.info("Captcha successful, sending email...")
        send_email(customer_email, customer_message)

    return server_response


def decode_body_to_dict(encoded_body):
    """function to decode message"""
    base64_bytes = encoded_body.encode("utf8")
    encoded_body_bytes = base64.b64decode(base64_bytes)
    decoded_body = encoded_body_bytes.decode("utf8")

    string_dict = {
        key: unquote(value.replace("+", " "))
        for key, value in [
            map(str.strip, item.split("=", 1))
            for item in decoded_body.split("&")
            if "=" in item
        ]
    }
    return string_dict


def html_response(body_content):
    """function to create html response"""
    return {
        "statusCode": 200,
        "body": f"""\
<html>
<head></head>
  <body>
    <p>{body_content}</p>
  </body>
</html>
""",
        "headers": {
            "Content-Type": "text/html",
        },
    }


def send_email(customer_email, customer_message):
    """Sends email to myself with details of message from contact form"""
    client = boto3.client("ses")
    text_email = f"""Hi Cullan!\n
    You've received a message from {customer_email}.\n
    They said: "{customer_message}".\n
    To reply, just reply to this email!"""

    html_email = f"""\
<html>
  <head></head>
  <body>
    <p>Hi Cullan!<br>
       You've received a message from {customer_email}<br>
       They said: "{customer_message}".<br>
       To reply, just reply to this email!
    </p>
  </body>
</html>
"""

    client.send_email(
        Source=f"noreply@{os.environ['website'].replace('form.', '')}",
        Destination={
            "ToAddresses": [
                "cullan@cullancarey.com",
            ]
        },
        Message={
            "Subject": {
                "Data": f"Inquiry from {os.environ['website'].replace('form.', '')}"
            },
            "Body": {"Text": {"Data": text_email}, "Html": {"Data": html_email}},
        },
        ReplyToAddresses=[
            customer_email,
        ],
    )


def verify_captcha(captcha_response, source_ip):
    """Function to verify the google captcha response"""
    http = urllib3.PoolManager()
    captcha_secret = get_param()
    request_response = http.request(
        "POST",
        "https://www.google.com/recaptcha/api/siteverify",
        fields={
            "secret": captcha_secret,
            "response": captcha_response,
            "remoteip": source_ip,
        },
    )
    request_values = json.loads(request_response.data.decode("utf-8"))
    if not request_values.get("success"):
        logger.error(
            f"Captcha failed due to error: {request_values.get('error-codes')}"
        )
        captcha_success = False
        server_response = json.dumps(
            {
                "statusCode": 403,
                "error": "Something went wrong. Please contact cullan@cullancarey.com.",
            }
        )
        return captcha_success, server_response
    captcha_success = True
    server_response = json.dumps(
        {
            "statusCode": 200,
            "message": "Thank you for your message! Cullan will get back to you shortly!",
        }
    )
    return captcha_success, server_response


def get_param():
    """Function to get parameter value from parameter store for captcha verification"""
    client = boto3.client("ssm")
    logger.info("Getting captcha parameter...")
    response = client.get_parameter(
        Name=f"{os.environ['environment']}_google_captcha_secret", WithDecryption=True
    )
    return response["Parameter"]["Value"]
