"""
Full pipeline: Stages 2-7 combined into your exact target output shape.

    USER CLAIM -> Disaster Detection -> Location Extraction ->
    Misinformation Model -> Official Source Verification ->
    Confidence + Priority Score

Reason text (in print_result) is generated from real values computed above
it -- not a canned string -- so it changes when the inputs do.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from disaster.disaster_classifier import KeywordDisasterClassifier
from location.location_extractor import GazetteerLocationExtractor
from misinformation.misinformation_classifier import TfidfLogRegClassifier
from verification.source_verifier import SourceVerifier
from utils.priority_scorer import score_priority

_disaster_clf = KeywordDisasterClassifier()
_location_ext = GazetteerLocationExtractor()
_misinfo_clf = TfidfLogRegClassifier()
_verifier = SourceVerifier()


def analyze_claim(text: str) -> dict:
    disaster = _disaster_clf.classify(text)
    location = _location_ext.extract(text)
    misinfo = _misinfo_clf.predict(text)
    verification = _verifier.verify(text)

    loc_best = location.best
    location_level = loc_best.match_level if loc_best else None
    disaster_type = disaster.primary_type if disaster.is_disaster_related else "None"

    def _best_key(m):
        return (m.locality, m.city, m.district, m.state)
    best_key = _best_key(loc_best) if loc_best else None

    priority = score_priority(text, disaster_type, location_level, misinfo.label)

    reason_parts = []
    if disaster.is_disaster_related:
        reason_parts.append(f"the claim matches '{disaster_type}'-type disaster keywords")
    if loc_best:
        reason_parts.append(f"a location was resolved at {location_level} level ({loc_best.state})")
    reason_parts.append(f"the model is {misinfo.confidence:.0%} confident in a {misinfo.label} verdict")
    if verification.matched:
        reason_parts.append(f"a similar claim ({verification.similarity:.0%} match) exists in the verified corpus")
    else:
        reason_parts.append("no matching record found in the verified corpus")
    reason = "; ".join(reason_parts)
    reason = reason[0].upper() + reason[1:] + "."

    return {
        "claim": text,
        "disaster_type": disaster_type,
        "all_disaster_types": disaster.disaster_types,
        "location": {
            "locality": loc_best.locality, "city": loc_best.city,
            "district": loc_best.district, "state": loc_best.state,
            "match_level": loc_best.match_level,
        } if loc_best else None,
        # Each entry below keeps the original "text"/"state"/"level" keys
        # unchanged (existing callers -- print_result -- only read those)
        # and additively includes the rest of the LocationMatch breakdown,
        # needed by the backend to persist one full Location row per
        # mention rather than just the primary one.
        "all_locations": [
            {
                "text": m.matched_text, "state": m.state, "level": m.match_level,
                "locality": m.locality, "city": m.city, "district": m.district,
                "match_type": m.match_type, "confidence": m.confidence,
                "pin_code": m.pincode,
                "is_primary": bool(loc_best) and _best_key(m) == best_key,
            }
            for m in location.locations
        ],
        "prediction": misinfo.label,
        "confidence": f"{misinfo.confidence:.0%}",
        "confidence_raw": misinfo.confidence,  # additive: raw 0-1 float, for callers that need a number not a string
        "top_terms": misinfo.top_terms,
        "verification": {
            "matched": verification.matched,
            "similarity": f"{verification.similarity:.0%}",
            "similarity_raw": verification.similarity,  # additive: raw 0-1 float
            "matched_claim": verification.matched_claim,
            "note": verification.source_note,
        },
        "priority": priority.level,
        "priority_score": priority.score,
        "priority_reasons": priority.reasons,
        "reason": reason,
    }


def print_result(r: dict):
    print(f"\nClaim: {r['claim']}")
    print(f"Prediction: {r['prediction']}")
    print(f"Confidence: {r['confidence']}")
    print(f"\nDisaster Type: {r['disaster_type']}")
    if len(r["all_locations"]) > 1:
        others = ", ".join(f"{l['text']} ({l['state']})" for l in r["all_locations"])
        print(f"Location: {r['location']['locality'] or r['location']['city'] or r['location']['state']}, "
              f"{r['location']['state']}   [multiple locations mentioned: {others}]")
    elif r["location"]:
        loc = r["location"]
        parts = [p for p in [loc["locality"], loc["city"], loc["district"], loc["state"]] if p]
        print(f"Location: {', '.join(dict.fromkeys(parts))}")
    else:
        print("Location: none detected")
    print(f"\nPriority: {r['priority']} (score={r['priority_score']})")
    print(f"\nReason:\n{r['reason']}")
    print(f"\nVerification:")
    if r["verification"]["matched"]:
        print(f"  Matching record found ({r['verification']['similarity']} similarity): "
              f"\"{r['verification']['matched_claim']}\"")
    else:
        print(f"  No matching official/verified record found.")
    print(f"  ({r['verification']['note']})")


if __name__ == "__main__":
    samples = [
        "Heavy rainfall has caused severe flooding in Whitefield, Bengaluru.",
        "Old video of 2019 Kerala floods being shared as visuals from the current Assam flooding",
        "NDRF teams conduct rescue operation after cyclone Fani hits Odisha coast",
    ]
    for s in samples:
        print_result(analyze_claim(s))
        print("\n" + "=" * 70)
