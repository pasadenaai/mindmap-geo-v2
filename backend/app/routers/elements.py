"""Periodic table elements — read and update endpoints."""
from fastapi import APIRouter, Body, HTTPException
from app.repositories import dynamo

router = APIRouter(prefix="/geo/elements", tags=["elements"])


@router.get("")
async def list_elements():
    return await dynamo.list_elements()


@router.get("/symbol/{symbol}")
async def get_element_by_symbol(symbol: str):
    element = await dynamo.get_element_by_symbol(symbol)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element with symbol '{symbol}' not found")
    return element


@router.get("/{atomic_number}")
async def get_element(atomic_number: str):
    element = await dynamo.get_element(atomic_number)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element {atomic_number} not found")
    return element


@router.put("/{atomic_number}")
async def upsert_element(atomic_number: str, data: dict = Body(...)):
    """Insert or replace an element record. Useful for enriching individual elements over time."""
    data["atomic_number"] = atomic_number
    return await dynamo.upsert_element(data)


# ── Country-element reserves ──────────────────────────────────────────────────

@router.get("/country/{cca2}")
async def get_country_elements(cca2: str):
    """Return the element-reserve profile for a country (ISO alpha-2 code)."""
    record = await dynamo.get_country_elements(cca2)
    if not record:
        return {"cca2": cca2.upper(), "elements": []}
    return record


@router.put("/country/{cca2}")
async def upsert_country_elements(cca2: str, data: dict = Body(...)):
    """Insert or replace the element-reserve profile for a country."""
    data["cca2"] = cca2.upper()
    return await dynamo.upsert_country_elements(data)
