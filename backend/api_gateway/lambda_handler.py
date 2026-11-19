"""AWS Lambda handler for the FastAPI app via Mangum."""
from mangum import Mangum

from api.main import app

handler = Mangum(app, lifespan="off")