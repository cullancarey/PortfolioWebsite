import boto3
import os
import json
import urllib.request


def send_cfn_response(event, context, status, reason=None, data=None):
    response_body = {
        "Status": status,
        "Reason": reason
        or f"See the details in CloudWatch Log Stream: {context.log_stream_name}",
        "PhysicalResourceId": context.log_stream_name,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
        "Data": data or {},
    }

    json_response_body = json.dumps(response_body)
    headers = {"content-type": "", "content-length": str(len(json_response_body))}

    try:
        request = urllib.request.Request(
            url=event["ResponseURL"],
            data=json_response_body.encode("utf-8"),
            headers=headers,
            method="PUT",
        )
        with urllib.request.urlopen(request) as response:
            print(f"CFN response status: {response.status}, reason: {response.reason}")
    except Exception as e:
        print(f"Failed to send CFN response: {e}")


def lambda_handler(event, context):
    print("Received event:", json.dumps(event))
    ssm_src = boto3.client("ssm", region_name=os.environ["SOURCE_REGION"])
    ssm_dst = boto3.client("ssm", region_name=os.environ["TARGET_REGION"])

    try:
        parameters = json.loads(os.environ["PARAMETERS"])
        for param in parameters:
            response = ssm_src.get_parameter(Name=param["source"])
            ssm_dst.put_parameter(
                Name=param["target"],
                Value=response["Parameter"]["Value"],
                Type="String",
                Overwrite=True,
            )
        send_cfn_response(
            event, context, status="SUCCESS", data={"Message": "Replication complete"}
        )
    except Exception as e:
        print(f"Error replicating parameters: {e}")
        send_cfn_response(event, context, status="FAILED", reason=str(e))
