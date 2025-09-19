FROM public.ecr.aws/lambda/python:3.13

# Copy function code
COPY ssm_param_replicator.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "ssm_param_replicator.lambda_handler" ]