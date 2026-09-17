"""Jurisdictions API route."""

from typing import List
from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(prefix="/jurisdictions", tags=["Jurisdictions"])


class JurisdictionInfo(BaseModel):
    name: str
    code: str
    status: str
    description: str


@router.get(
    "",
    response_model=List[JurisdictionInfo],
    status_code=status.HTTP_200_OK,
    summary="List Supported Jurisdictions",
    description="Returns the list of legal jurisdictions supported by the decision-support engine.",
)
def get_supported_jurisdictions() -> List[JurisdictionInfo]:
    return [
        JurisdictionInfo(
            name="India",
            code="IN",
            status="active",
            description="Full statutory coverage: Patents Act 1970 (Sec 3p), Drugs & Cosmetics Act 1940 (ASU), FSSAI Ayurveda Aahar, and Biological Diversity Act 2002.",
        ),
        JurisdictionInfo(
            name="International",
            code="INT",
            status="active",
            description="Multilateral frameworks: WIPO Traditional Knowledge Intergovernmental Committee, Patent Cooperation Treaty (PCT), and Nagoya Protocol.",
        ),
        JurisdictionInfo(
            name="USA",
            code="US",
            status="supported",
            description="US Patent and Trademark Office (USPTO 35 U.S.C. 101/102/103) & US FDA Botanical Drug Guidance.",
        ),
        JurisdictionInfo(
            name="European Union",
            code="EU",
            status="supported",
            description="European Patent Office (EPO Art 52/54/56) & EMA Traditional Herbal Medicinal Products Directive (Directive 2004/24/EC).",
        ),
        JurisdictionInfo(
            name="UK",
            code="UK",
            status="supported",
            description="UK Intellectual Property Office (UKIPO) & MHRA Traditional Herbal Medicines Registration (THR).",
        ),
        JurisdictionInfo(
            name="Japan",
            code="JP",
            status="supported",
            description="Japan Patent Office (JPO) & PMDA Kampo Medicine Regulations.",
        ),
    ]
