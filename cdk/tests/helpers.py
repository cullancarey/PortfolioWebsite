from __future__ import annotations

from aws_cdk.assertions import Template


def collect_allowed_actions(template: Template) -> list[str]:
    """Collect every allowed IAM action from a synthesized template."""
    actions: list[str] = []
    for policy in template.find_resources("AWS::IAM::Policy").values():
        statements = policy["Properties"]["PolicyDocument"]["Statement"]
        if not isinstance(statements, list):
            statements = [statements]
        for statement in statements:
            if statement.get("Effect") != "Allow":
                continue
            action = statement.get("Action", [])
            if isinstance(action, str):
                actions.append(action)
            else:
                actions.extend(action)
    return actions


def collect_ssm_resources(template: Template) -> list[str]:
    """Collect all SSM IAM resources from a synthesized template."""
    resources: list[str] = []
    for policy in template.find_resources("AWS::IAM::Policy").values():
        statements = policy["Properties"]["PolicyDocument"]["Statement"]
        if not isinstance(statements, list):
            statements = [statements]
        for statement in statements:
            if statement.get("Effect") != "Allow":
                continue
            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            if any(action.startswith("ssm:") for action in actions):
                resource = statement.get("Resource", [])
                if isinstance(resource, str):
                    resources.append(resource)
                else:
                    resources.extend(resource)
    return resources
