import json


def score_facultative_risks(data):
    results = []

    for case in data:
        
        # Primary decision makers
        decision_reasons = []

        # Rule 1: Loss Ratio threshold
        loss_ratio_pct = case.get("Loss_Ratio_Pct")
        if loss_ratio_pct is None:
            decision_reasons.append("Loss ratio not available (insufficient data)")
            loss_ratio_ok = True  # Default to acceptable when data is missing
        elif loss_ratio_pct <= 80:
            decision_reasons.append(f"Loss ratio {round(loss_ratio_pct, 2)}% is <= 80% (acceptable)")
            loss_ratio_ok = True
        else:
            decision_reasons.append(f"Loss ratio {round(loss_ratio_pct, 2)}% is > 80% (reject)")
            loss_ratio_ok = False

        # Rule 2: Maximum liability threshold
        # Use Accepted_Liability_KES if available, else approximate from TSI and offered share
        accepted_liability = case.get("Accepted_Liability_KES")
        if accepted_liability is None:
            tsi_kes = case.get("TSI_KES") or case.get("TSI_Original_Currency") or 0
            share_offered_pct = case.get("Share_Offered_Pct", 0)
            try:
                accepted_liability = (float(tsi_kes) * float(share_offered_pct)) / 100.0
            except (TypeError, ValueError):
                accepted_liability = 0
        max_liability_ok = accepted_liability < 1_000_000_000
        if max_liability_ok:
            decision_reasons.append(f"Accepted liability {int(accepted_liability)} KES is < 1,000,000,000 KES (acceptable)")
        else:
            decision_reasons.append(f"Accepted liability {int(accepted_liability)} KES is >= 1,000,000,000 KES (reject)")

        # Final decision
        if loss_ratio_ok and max_liability_ok:
            decision = "Accept"
            offered = case.get("Share_Offered_Pct", 0)
            accepted_share = offered if offered is not None else 0
        else:
            decision = "Decline"
            accepted_share = 0

        # Persist outputs
        case["Decision"] = decision
        case["Accepted_Share_Pct"] = round(accepted_share, 2) if accepted_share is not None else 0
        case["Decision_Reasons"] = decision_reasons
        case["Decision_Rationale"] = "; ".join(decision_reasons)
        case["Evaluated_Loss_Ratio_Pct"] = loss_ratio_pct
        case["Evaluated_Accepted_Liability_KES"] = accepted_liability

        results.append(case)

    return results


# Example usage
if __name__ == "__main__":
    input_path = "/home/gichinga/Desktop/projects/AI4INSURANCE/backend/calcultaions/facultative_reinsurance_calculations.json"
    output_path = "/home/gichinga/Desktop/projects/AI4INSURANCE/backend/FINAL/decisions.json"

    with open(input_path, "r") as f:
        data = json.load(f)

    output = score_facultative_risks(data)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(json.dumps(output, indent=2))
