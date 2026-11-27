"""AWS Lambda handler for the FastAPI app via Mangum."""
from mangum import Mangum

from backend.api_gateway.main import app

handler = Mangum(app, lifespan="off")