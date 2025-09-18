FROM public.ecr.aws/lambda/python:3.13

# Copy function code
COPY contact_form_intake.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "contact_form_intake.lambda_handler" ]