import requests
import random
import json
from typing import Any, Dict, List, Optional

# --------------------------
# Safe numeric coercion
# --------------------------

def _safe_float(v: Any) -> float:
    try:
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace(',', '')
        if s == '' or s.lower() in {'nan', 'none', 'null'}:
            return 0.0
        return float(s)
    except Exception:
        return 0.0

# --------------------------
# CAT Exposure (Earthquake, Flood, Typhoon)
# --------------------------

def get_cat_exposure(lat: Optional[float], lon: Optional[float]) -> Dict[str, str]:
    # If coordinates are missing, return conservative defaults
    if lat is None or lon is None:
        return {"Earthquake": "Low", "Flood": "Moderate", "Typhoon": "Low"}

    # Fetch recent earthquake data from USGS (robust with filtering and timeouts)
    try:
        response = requests.get(
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            params={
                "format": "geojson",
                "latitude": lat,
                "longitude": lon,
                "maxradiuskm": 100,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        data = {"features": []}

    # Determine earthquake hazard level based on recent events
    features = data.get("features", [])
    magnitudes: List[float] = []
    for event in features:
        mag = event.get("properties", {}).get("mag")
        if isinstance(mag, (int, float)):
            magnitudes.append(float(mag))

    if magnitudes:
        avg_magnitude = sum(magnitudes) / len(magnitudes)
        if avg_magnitude >= 6.0:
            earthquake_risk = "High"
        elif avg_magnitude >= 4.0:
            earthquake_risk = "Moderate"
        else:
            earthquake_risk = "Low"
    else:
        earthquake_risk = "Low"

    # For flood and typhoon, mock values
    flood_risk = "Moderate"
    typhoon_risk = "Low"

    return {
        "Earthquake": earthquake_risk,
        "Flood": flood_risk,
        "Typhoon": typhoon_risk,
    }

# --------------------------
# Climate / ESG Risk
# --------------------------

def get_climate_esg_risk(industry: str, tsi: float) -> Dict[str, str]:
    climate_risk = "High" if industry in ["Cold Storage", "Agriculture", "Power Generation"] else "Medium"
    esg_risk = "Low" if tsi > 500e6 else "Medium"
    return {"ClimateRisk": climate_risk, "ESGRisk": esg_risk}

# --------------------------
# Market Considerations
# --------------------------

def get_market_conditions(industry: str) -> Dict[str, float]:
    market_rates = {
        "Cold Storage": random.uniform(2.0, 3.5),  # ‰
        "Manufacturing": random.uniform(1.5, 3.0),
        "Healthcare": random.uniform(1.0, 2.5),
        "Power Generation": random.uniform(2.5, 4.5),
        "Shipping Services": random.uniform(1.8, 3.2),
    }
    return {"CompetitorRate_per_mille": round(market_rates.get(industry, 2.0), 2)}

# --------------------------
# Portfolio Impact
# --------------------------

def compute_portfolio_impact(existing_portfolio_tsi: List[float], new_tsi: float) -> Dict[str, Any]:
    total_tsi = sum(existing_portfolio_tsi) + (_safe_float(new_tsi) or 0.0)
    concentration = (_safe_float(new_tsi) or 0.0) / total_tsi if total_tsi else 0.0
    if concentration < 0.1:
        impact = "Low"
    elif concentration < 0.3:
        impact = "Medium"
    else:
        impact = "High"
    return {"PortfolioImpact": impact, "Concentration": concentration}

# --------------------------
# Proposed % Share
# --------------------------

def propose_share(pml_percent: float, cat_exposure: Dict[str, str], retention_percent: float, portfolio_impact: Dict[str, Any]) -> Dict[str, float]:
    risk_score = _safe_float(pml_percent) or 0.0
    for v in cat_exposure.values():
        if v == "High":
            risk_score += 10
        elif v == "Moderate":
            risk_score += 5

    if portfolio_impact.get("PortfolioImpact") == "High":
        risk_score += 10

    proposed_share = max(0.0, min(100.0 - (_safe_float(retention_percent) or 0.0), 100.0 - risk_score))
    return {"ProposedShare_percent": round(proposed_share, 2)}

# --------------------------
# Actuarial helpers
# --------------------------

def safe_pct(value: float) -> float:
    return round(value, 10)


def compute_actuarial_fields(r: Dict[str, Any]) -> Dict[str, Any]:
    tsi = _safe_float(r.get("TSI_Original_Currency", 0))
    premium = _safe_float(r.get("Premium_Original_Currency", 0))
    pml_pct = _safe_float(r.get("PML_Pct", 0))
    retention_pct = _safe_float(r.get("Retention_of_Cedant_Pct", 0))
    share_offered_pct = _safe_float(r.get("Share_Offered_Pct", 0))

    tsi_base = tsi
    premium_base = premium

    premium_rate_percentage = (premium_base / tsi_base * 100.0) if tsi_base else 0.0
    premium_rate_permille = premium_rate_percentage * 10.0 / 1.0

    paid = _safe_float(r.get("Paid_Losses_3_Years", 0))
    outstanding = _safe_float(r.get("Outstanding_Reserves_3_Years", 0))
    recoveries = _safe_float(r.get("Recoveries_3_Years", 0))
    earned = _safe_float(r.get("Earned_Premium_3_Years", 0))
    loss_ratio = ((paid + outstanding - recoveries) / earned * 100.0) if earned else 0.0

    accepted_liability = tsi_base * (share_offered_pct / 100.0)
    accepted_premium = premium_base * (share_offered_pct / 100.0)

    pml_amount = tsi_base * (pml_pct / 100.0)
    retention_amount = tsi_base * (retention_pct / 100.0)

    return {
        "TSI_KES": round(tsi_base, 2),
        "Premium_KES": round(premium_base, 2),
        "Premium_Rate_Percentage": safe_pct(premium_rate_percentage),
        "Premium_Rate_Permille": safe_pct(premium_rate_permille),
        "Loss_Ratio_Pct": safe_pct(loss_ratio),
        "Accepted_Premium_KES": round(accepted_premium, 2),
        "Accepted_Liability_KES": round(accepted_liability, 2),
        "PML_Amount_KES": round(pml_amount, 2),
        "Retention_Amount_KES": round(retention_amount, 2),
    }

# --------------------------
# Batch processing main
# --------------------------

existing_portfolio = [200e6, 150e6, 300e6]  # Other TSI in base currency


def enrich_risk_record(r: Dict[str, Any]) -> Dict[str, Any]:
    industry = r.get("Occupation_of_Insured") or r.get("Main_Activities") or "Manufacturing"
    tsi = _safe_float(r.get("TSI_Original_Currency", 0))

    # Coordinates are optional in input
    lat = r.get("latitude")
    lon = r.get("longitude")
    try:
        lat = float(lat) if lat is not None else None
    except Exception:
        lat = None
    try:
        lon = float(lon) if lon is not None else None
    except Exception:
        lon = None

    cat_exposure = get_cat_exposure(lat, lon)
    climate_esg = get_climate_esg_risk(industry, tsi)
    market = get_market_conditions(industry)
    portfolio = compute_portfolio_impact(existing_portfolio, tsi)

    pml_pct = _safe_float(r.get("PML_Pct", 0))
    retention_pct = _safe_float(r.get("Retention_of_Cedant_Pct", 0))
    proposed_share = propose_share(pml_pct, cat_exposure, retention_pct, portfolio)

    actuarial = compute_actuarial_fields(r)

    enriched: Dict[str, Any] = dict(r)  # keep original keys
    enriched.update(actuarial)
    enriched.update({
        "CAT_Exposure": cat_exposure,
        "Climate_ESG_Risk": climate_esg,
        "Market_Considerations": market,
        "Portfolio_Impact": portfolio,
        "Proposed_Share": proposed_share,
    })
    return enriched


def load_input(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("sample_input.json must contain a list of risks")
        return data


def write_output(path: str, records: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


if __name__ == "__main__":
    input_path = "/home/gichinga/Desktop/projects/AI4INSURANCE/backend/calcultaions/sample_input.json"
    output_path = "/home/gichinga/Desktop/projects/AI4INSURANCE/backend/calcultaions/facultative_reinsurance_calculations.json"

    risks = load_input(input_path)
    enriched_records = [enrich_risk_record(r) for r in risks]
    write_output(output_path, enriched_records)

    # Also print a brief summary to stdout
    print(json.dumps({
        "records_processed": len(enriched_records),
        "output_file": output_path,
    }, indent=2))
