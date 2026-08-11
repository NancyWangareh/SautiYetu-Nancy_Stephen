from fastapi import APIRouter, Depends

from ..schemas.submission import ClassifyRequest, ClassifyResponse
from ..dependencies import get_classifier
from ..services.classifier import ClassifierService

router = APIRouter(prefix="/api/submissions", tags=["classification"])


@router.post("/classify", response_model=ClassifyResponse)
async def classify_text(
    payload: ClassifyRequest,
    classifier: ClassifierService = Depends(get_classifier),
):
    """
    Lightweight classification preview — no DB write.
    Used by the frontend for real-time classification as the user types.
    """
    result = await classifier.classify(payload.text)
    return ClassifyResponse(
        sector=result["sector"],
        sub_sector=result["sub_sector"],
        confidence=result["confidence"],
    )