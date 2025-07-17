import json
import pytest
from unittest.mock import patch

from assets.lambdas.contact_form_intake.contact_form_intake import lambda_handler


@pytest.fixture
def valid_event():
    body = json.dumps(
        {
            "CustomerEmail": "test@example.com",
            "CustomerName": "Tester",
            "MessageDetails": "This is a test message.",
            "g-recaptcha-response": "test-captcha-token",
        }
    )
    return {
        "headers": {"content-type": "application/json"},
        "body": body,
        "isBase64Encoded": False,
        "requestContext": {"http": {"sourceIp": "127.0.0.1"}},
    }


@patch("assets.lambdas.contact_form_intake.contact_form_intake.send_email")
@patch("assets.lambdas.contact_form_intake.contact_form_intake.verify_captcha")
def test_lambda_handler_valid_request(mock_verify, mock_send, valid_event):
    mock_verify.return_value = True
    mock_send.return_value = None

    response = lambda_handler(valid_event, None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert "Cullan will get back to you" in body["message"]
    mock_send.assert_called_once()


@patch("assets.lambdas.contact_form_intake.contact_form_intake.verify_captcha")
def test_lambda_handler_invalid_captcha(mock_verify, valid_event):
    mock_verify.return_value = False
    response = lambda_handler(valid_event, None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 403
    assert "Captcha verification failed." in body["error"]


def test_lambda_handler_missing_fields():
    event = {
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"foo": "bar"}),
        "isBase64Encoded": False,
        "requestContext": {"http": {"sourceIp": "127.0.0.1"}},
    }
    response = lambda_handler(event, None)
    assert response["statusCode"] == 400


def test_lambda_handler_invalid_content_type(valid_event):
    valid_event["headers"]["content-type"] = "text/plain"
    response = lambda_handler(valid_event, None)
    assert response["statusCode"] == 400
    assert "Invalid content type" in response["body"]


def test_lambda_handler_botcheck_field(valid_event):
    valid_event["body"] = json.dumps(
        {
            "CustomerEmail": "test@example.com",
            "CustomerName": "Tester",
            "MessageDetails": "This is a test message.",
            "g-recaptcha-response": "test-captcha-token",
            "BotCheck": "on",
        }
    )
    response = lambda_handler(valid_event, None)
    assert response["statusCode"] == 200
    assert "bot detected" in response["body"]
