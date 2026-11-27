# Container image for the API Lambda (7_frontend, package_type = "Image").
#
# The API imports most of backend/ and most of the root requirements.txt, which
# does not fit in a 250 MB zip Lambda; container images may be up to 10 GB.
# Build from the repo root:
#   docker buildx build --platform linux/amd64 --provenance=false \
#     -f infrastructure/docker/api-lambda.Dockerfile -t <uri> .
# Its ignore file is api-lambda.Dockerfile.dockerignore next to this file.
FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt "mangum>=0.19.0,<1.0.0" \
    && rm /tmp/requirements.txt

COPY backend/ ${LAMBDA_TASK_ROOT}/backend/

CMD ["backend.api_gateway.lambda_handler.handler"]
