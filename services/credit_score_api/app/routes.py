from fastapi import APIRouter

router = APIRouter()

@router.get("/credit-score")
def get_credit_score(customer_id: str):
    return {"customer_id": customer_id, "score": 750}
