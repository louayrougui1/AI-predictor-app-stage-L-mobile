import logging
import random

from fastapi import APIRouter, Request,Depends

from app.auth import api_messages, dependencies
from app.auth.models import User
from app.core.rate_limit import check_rate_limit

from app.prediction.schemas import (
    ModelRequest,
    ModelResponse,
)

router = APIRouter(responses=api_messages.UNAUTHORIZED_RESPONSES)
logger = logging.getLogger(__name__)



@router.post("/", description="Predict")
async def predict(request: Request,model_request: ModelRequest, user: User = Depends(dependencies.get_current_user))-> ModelResponse:
    await check_rate_limit(request, user.email, key_limit=15, window=60)

    prediction=get_prediction(model_request)
    model_response =ModelResponse(prediction=prediction)
    return model_response

def get_prediction(model_request: ModelRequest) -> int:
    # call mt3 el model here and return the prediction
    return random.randint(10,20)