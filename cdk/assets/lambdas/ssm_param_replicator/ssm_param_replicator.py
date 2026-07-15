import boto3
import json


def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    request_type = event.get("RequestType", "Create")
    resource_props = event.get("ResourceProperties", {})

    source_region = resource_props["SourceRegion"]
    target_region = resource_props["TargetRegion"]

    parameters_raw = resource_props["Parameters"]
    parameters = (
        json.loads(parameters_raw)
        if isinstance(parameters_raw, str)
        else parameters_raw
    )

    physical_resource_id = event.get(
        "PhysicalResourceId", f"ssm-param-replicator-{source_region}-to-{target_region}"
    )

    if request_type == "Delete":
        # Nothing to clean up. Source and target SSM params are managed elsewhere.
        return {
            "PhysicalResourceId": physical_resource_id,
            "Data": {"Message": "Delete - nothing to do"},
        }

    ssm_src = boto3.client("ssm", region_name=source_region)
    ssm_dst = boto3.client("ssm", region_name=target_region)

    try:
        for param in parameters:
            response = ssm_src.get_parameter(Name=param["source"])
            ssm_dst.put_parameter(
                Name=param["target"],
                Value=response["Parameter"]["Value"],
                Type="String",
                Overwrite=True,
            )

        return {
            "PhysicalResourceId": physical_resource_id,
            "Data": {
                "Message": "Replication complete",
                "ReplicatedCount": len(parameters),
            },
        }
    except Exception as e:
        print(f"Error replicating parameters: {e}")
        # With custom_resources.Provider, raise to signal failure.
        raise
