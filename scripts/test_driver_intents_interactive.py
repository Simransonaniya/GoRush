"""
Interactive / Batch Tester for Driver Chatbot Intents
Usage: python scripts/test_driver_intents_interactive.py ["sample driver query"]
"""
import sys
from app.ai.intent.detector import intent_detector

SAMPLE_DRIVER_QUERIES = [
    "I am not receiving any ride offers",
    "Booking offer nahi aa raha hai",
    "Cannot accept ride request",
    "Duty accept nahi ho rahi",
    "Customer is not at the pickup location",
    "Pickup spot par rider missing hai, call nahi utha raha",
    "Customer cancelled the ride halfway",
    "GPS navigation is taking me to wrong route",
    "App freeze ho raha hai while taking ride",
    "Show my daily earnings for today",
    "Haftewari kamai kitni hui hai?",
    "My weekly payout status is pending",
    "Bank transfer payout delay ho gaya hai",
    "Check my peak hour bonus incentive status",
    "My driving license is near expiry",
    "I want to change vehicle in my driver profile",
    "Customer didn't pay cash for the trip",
    "Emergency SOS accident on the road",
]


def test_phrase(phrase: str):
    res = intent_detector.detect(phrase)
    print(f"\nQuery:         \"{phrase}\"")
    print(f"Detected Intent: {res.intent.value}")
    print(f"Confidence:      {res.confidence}")
    print(f"Language:        {res.language.value if hasattr(res.language, 'value') else res.language}")
    print(f"Urgency:         {res.urgency.value if hasattr(res.urgency, 'value') else res.urgency}")
    print(f"Requires Tool:   {res.requires_tool}")
    print(f"Risk Level:      {res.risk_level.value if hasattr(res.risk_level, 'value') else res.risk_level}")
    print("-" * 50)


def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        test_phrase(query)
    else:
        print("=== Running Driver Intent Test Batch ===")
        for query in SAMPLE_DRIVER_QUERIES:
            test_phrase(query)


if __name__ == "__main__":
    main()
