from fastapi import APIRouter

router = APIRouter()

@router.get("/aadhaar/verify")
def verify_aadhaar(aadhaar_number: str):
    return {"aadhaar_number": aadhaar_number, "valid": True}
