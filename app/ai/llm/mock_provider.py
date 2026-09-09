"""
Mock LLM provider.

Provides deterministic, context-aware, localized driver & customer support responses
for development & testing across all supported languages (EN, HI, PA, GU, RAJ, HINGLISH, etc.).
"""

from collections.abc import AsyncIterator
from typing import Any
import json
import re

from app.ai.llm.provider import ChatMessage, LLMProvider, LLMResponse, ToolSpec
from app.core.config import get_settings


class MockLLMProvider(LLMProvider):
    def __init__(self, model: str | None = None):
        self.model = model or "mock-v1"

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        last_user_msg = next(
            (m.content for m in reversed(messages) if m.role == "user"), ""
        )
        sys_prompt = system or ""
        msg_lower = last_user_msg.lower()

        all_text = (sys_prompt + " " + " ".join(m.content for m in messages if m.content)).lower()

        sys_lower = sys_prompt.lower()
        is_raj = "communicating in rajasthani" in sys_lower or "rajasthani script" in sys_lower or any(w in last_user_msg for w in ["कोनी", "कर्यो", "नै", "थारो", "म्हारे"]) or "koni" in msg_lower
        is_punjabi = "communicating in punjabi" in sys_lower or "gurmukhi" in sys_lower or any(c in last_user_msg for c in "ਗਾਹਕਕੀਤਾਨਹੀਂਹੋਇਆਭੁਗਤਾਨ") or "tusi" in msg_lower or "kiti" in msg_lower
        is_gujarati = "communicating in gujarati" in sys_lower or "gujarati script" in sys_lower or any(c in last_user_msg for c in "ગ્રાહકેચુકવણીનથીથઈકરી") or "nathi" in msg_lower or "tamare" in msg_lower
        is_bengali = "communicating in bengali" in sys_lower or "bengali script" in sys_lower or any(w in last_user_msg for w in ["করেনি", "টাকা", "পেমেন্ট", "বিরোধ"])
        is_marathi = "communicating in marathi" in sys_lower or "marathi script" in sys_lower or any(w in last_user_msg for w in ["केले", "नाही", "ग्राहकाने", "झाले"])
        is_hindi = ("communicating in hindi" in sys_lower or any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in last_user_msg)) and not is_raj and not is_marathi
        is_hinglish = "communicating in hinglish" in sys_lower or (any(w in msg_lower for w in ["nahi", "hai", "karo", "raha", "kya", "paisa", "payment", "start"]) and not is_raj and not is_punjabi and not is_gujarati and not is_bengali and not is_marathi and not is_hindi and any(ord(c) < 128 for c in last_user_msg))

        # Check if the last message in conversation history contains tool execution feedback
        last_msg = messages[-1] if messages else None
        if last_msg and last_msg.role == "user" and last_msg.content and last_msg.content.startswith("Tool "):
            feedback = last_msg.content

            # 1. Needs user confirmation
            if "needs user confirmation" in feedback:
                if "create_support_ticket" in feedback or "dispute" in feedback:
                    if is_bengali:
                        reply = "পেমেন্ট বিরোধ শুরু করার জন্য নিশ্চিতকরণ প্রয়োজন। আপনি কি পেমেন্ট বিরোধ শুরু করতে চান?"
                    elif is_marathi:
                        reply = "पेमेंट तक्रार नोंदवण्यासाठी खात्री आवश्यक आहे. तुम्ही पेमेंट तक्रार नोंदवू इच्छिता का?"
                    elif is_raj:
                        reply = "पेमेंट विवाद शुरू करवा खातर पुष्टि री आवश्यकता है। काईं आप पेमेंट विवाद शुरू करबो चाहो?"
                    elif is_punjabi:
                        reply = "ਭੁਗਤਾਨ ਵਿਵਾਦ ਸ਼ੁਰੂ ਕਰਨ ਲਈ ਪੁਸ਼ਟੀ ਦੀ ਲੋੜ ਹੈ। ਕੀ ਤੁਸੀਂ ਭੁਗਤਾਨ ਵਿਵਾਦ ਸ਼ੁਰੂ ਕਰਨਾ ਚਾਹੁੰਦੇ ਹੋ?"
                    elif is_gujarati:
                        reply = "ચુકવણી વિવાદ શરૂ કરવા માટે પુષ્ટિ જરૂરી છે. શું તમે ચુકવણી વિવાદ શરૂ કરવા માંગો છો?"
                    elif is_hindi:
                        reply = "पेमेंट विवाद शुरू करने के लिए पुष्टि की आवश्यकता है। क्या आप पेमेंट विवाद शुरू करना चाहते हैं?"
                    elif is_hinglish:
                        reply = "Payment dispute start karne ke liye confirmation chahiye. Kya aap payment dispute start karna chahte hain?"
                    else:
                        reply = "Confirmation is required to start a payment dispute. Would you like to proceed with starting the payment dispute?"
                elif "cancel_ride" in feedback:
                    if is_hindi:
                        reply = "राइड रद्द करने के लिए पुष्टि की आवश्यकता है। क्या आप राइड रद्द करना चाहते हैं?"
                    elif is_hinglish:
                        reply = "Ride cancel karne ke liye confirmation chahiye. Kya aap ride cancel karna chahte hain?"
                    else:
                        reply = "Confirmation is required to cancel your ride. Would you like to proceed with cancelling the ride?"
                elif "request_refund" in feedback:
                    if is_hindi:
                        reply = "रिफंड अनुरोध के लिए पुष्टि की आवश्यकता है। क्या आप रिफंड प्रक्रिया शुरू करना चाहते हैं?"
                    elif is_hinglish:
                        reply = "Refund request process karne ke liye confirmation chahiye. Kya aap refund request submit karna chahte hain?"
                    else:
                        reply = "Confirmation is required to process your refund request. Would you like to proceed?"
                else:
                    if is_hinglish:
                        reply = "Yeh action perform karne ke liye confirmation chahiye. Kya aap proceed karna chahte hain?"
                    else:
                        reply = "Confirmation is required before performing this action. Would you like to proceed?"
                return LLMResponse(text=reply, tool_calls=[], model=self.model, input_tokens=10, output_tokens=20)

            # 2. Tool execution result (SUCCESS)
            elif "result:" in feedback:
                if "get_active_ride" in feedback:
                    ride = None
                    try:
                        match = re.search(r"result:\s*(\{.*\})", feedback)
                        if match:
                            res_dict = json.loads(match.group(1))
                            ride = res_dict.get("ride")
                    except Exception:
                        pass
                    if ride:
                        ride_id = ride.get("ride_id", "ride_123")
                        status = ride.get("status", "active")
                        driver_id = ride.get("driver_id", "drv_9")
                        eta = ride.get("eta_minutes", 6)
                        if is_bengali:
                            reply = f"আপনার সক্রিয় রাইড ({ride_id}) স্ট্যাটাস '{status}'। ড্রাইভার: {driver_id}, ETA: {eta} মিনিট।"
                        elif is_marathi:
                            reply = f"तुमची ॲक्टिव्ह राइड ({ride_id}) स्थितीत '{status}' आहे. ड्रायव्हर: {driver_id}, ETA: {eta} मिनिटे."
                        elif is_raj:
                            reply = f"थारी एक्टिव राइड ({ride_id}) री स्थिति '{status}' है। ड्राइवर: {driver_id}, ETA: {eta} मिनट।"
                        elif is_punjabi:
                            reply = f"ਤੁਹਾਡੀ ਸਰਗਰਮ ਰਾਈਡ ({ride_id}) ਸਥਿਤੀ '{status}' ਹੈ। ਡ੍ਰਾਈਵਰ: {driver_id}, ETA: {eta} ਮਿੰਟ।"
                        elif is_gujarati:
                            reply = f"તમારી એક્ટિવ રાઇડ ({ride_id}) સ્થિતિ '{status}' છે. ડ્રાઇવર: {driver_id}, ETA: {eta} મિનિટ."
                        elif is_hindi:
                            reply = f"आपकी एक्टिव राइड ({ride_id}) की स्थिति '{status}' है। ड्राइवर: {driver_id}, ETA: {eta} मिनट।"
                        elif is_hinglish:
                            reply = f"Aapki active ride ({ride_id}) status '{status}' hai. Driver: {driver_id}, ETA: {eta} mins."
                        else:
                            reply = f"Your active ride ({ride_id}) status is '{status}'. Driver {driver_id} is assigned with an ETA of {eta} minutes."
                    else:
                        if is_bengali:
                            reply = "আপনার কোনো সক্রিয় রাইড নেই।"
                        elif is_marathi:
                            reply = "तुमच्याकडे कोणतीही ॲक्टिव्ह राइड नाही."
                        elif is_raj:
                            reply = "थारे पासा कोनी एक्टिव राइड कोनी।"
                        elif is_punjabi:
                            reply = "ਤੁਹਾਡੇ ਕੋਲ ਕੋਈ ਸਰਗਰਮ ਰਾਈਡ ਨਹੀਂ ਹੈ।"
                        elif is_gujarati:
                            reply = "તમારી પાસે કોઈ એક્ટિવ રાઇડ નથી."
                        elif is_hindi:
                            reply = "आपके पास वर्तमान में कोई एक्टिव राइड नहीं है।"
                        elif is_hinglish:
                            reply = "Aapke paas filhal koi active ride nahi hai."
                        else:
                            reply = "No active ride is currently assigned to you."
                elif "get_driver_eta" in feedback:
                    try:
                        match = re.search(r"result:\s*(\{.*\})", feedback)
                        res_dict = json.loads(match.group(1)) if match else {}
                        eta = res_dict.get("eta_minutes", 6)
                    except Exception:
                        eta = 6
                    if is_hindi:
                        reply = f"आपके ड्राइवर का अनुमानित आगमन समय (ETA) {eta} मिनट है।"
                    elif is_hinglish:
                        reply = f"Driver ka ETA {eta} mins hai."
                    else:
                        reply = f"The estimated time of arrival (ETA) for your driver is {eta} minutes."
                elif "get_ride_fare_breakdown" in feedback:
                    try:
                        match = re.search(r"result:\s*(\{.*\})", feedback)
                        res_dict = json.loads(match.group(1)) if match else {}
                        total = res_dict.get("total", 148.0)
                        base = res_dict.get("base_fare", 60.0)
                        dist = res_dict.get("distance_fare", 70.0)
                    except Exception:
                        total, base, dist = 148.0, 60.0, 70.0
                    if is_hindi:
                        reply = f"आपकी राइड का कुल किराया ₹{total} है (बेस फेयर: ₹{base}, डिस्टेंस फेयर: ₹{dist})।"
                    elif is_hinglish:
                        reply = f"Aapki ride ka total fare ₹{total} hai (base fare: ₹{base}, distance fare: ₹{dist})."
                    else:
                        reply = f"The total fare for your ride is ₹{total} (Base fare: ₹{base}, Distance fare: ₹{dist})."
                elif "get_payment_status" in feedback:
                    try:
                        match = re.search(r"result:\s*(\{.*\})", feedback)
                        res_dict = json.loads(match.group(1)) if match else {}
                        status = res_dict.get("status", "captured")
                        amount = res_dict.get("amount", 148.0)
                    except Exception:
                        status, amount = "captured", 148.0
                    if is_hindi:
                        reply = f"आपकी पेमेंट की स्थिति '{status}' है। कुल राशि: ₹{amount}।"
                    elif is_hinglish:
                        reply = f"Aapki payment status '{status}' hai. Amount: ₹{amount}."
                    else:
                        reply = f"Your payment status is '{status}' for amount ₹{amount}."
                elif "get_refund_status" in feedback:
                    try:
                        match = re.search(r"result:\s*(\{.*\})", feedback)
                        res_dict = json.loads(match.group(1)) if match else {}
                        status = res_dict.get("status", "not_requested")
                    except Exception:
                        status = "not_requested"
                    if is_hindi:
                        reply = f"आपके रिफंड की स्थिति '{status}' है।"
                    elif is_hinglish:
                        reply = f"Aapka refund status '{status}' hai."
                    else:
                        reply = f"Your refund status is '{status}'."
                elif "get_driver_earnings" in feedback:
                    try:
                        match = re.search(r"result:\s*(\{.*\})", feedback)
                        res_dict = json.loads(match.group(1)) if match else {}
                        gross = res_dict.get("gross_earnings", 742.50)
                        net = res_dict.get("net_earnings", 668.25)
                        trips = res_dict.get("trips", 8)
                        period = res_dict.get("period", "today")
                    except Exception:
                        gross, net, trips, period = 742.50, 668.25, 8, "today"
                    if is_hindi:
                        reply = f"आपकी {period} की कमाई: कुल {trips} ट्रिप्स, ग्रॉस: ₹{gross}, नेट कमाई: ₹{net}।"
                    elif is_hinglish:
                        reply = f"Aapki {period} ki earnings: Total {trips} trips, gross: ₹{gross}, net: ₹{net}."
                    else:
                        reply = f"Your {period} earnings breakdown: {trips} trips completed, gross earnings ₹{gross}, net earnings ₹{net}."
                elif "get_document_status" in feedback:
                    try:
                        match = re.search(r"result:\s*(\{.*\})", feedback)
                        res_dict = json.loads(match.group(1)) if match else {}
                        overall = res_dict.get("overall_status", "all_approved")
                        can_drive = res_dict.get("can_drive", True)
                    except Exception:
                        overall, can_drive = "all_approved", True
                    if is_hindi:
                        reply = f"आपके दस्तावेज़ों की स्थिति '{overall}' है। गाड़ी चलाने की अनुमति: {'हाँ' if can_drive else 'नहीं'}।"
                    elif is_hinglish:
                        reply = f"Aapke documents status '{overall}' hai. Driving status: {'Allowed' if can_drive else 'Not allowed'}."
                    else:
                        reply = f"Your document verification status is '{overall}'. Driving enabled: {can_drive}."
                elif "get_ticket_status" in feedback:
                    try:
                        match = re.search(r"result:\s*(\{.*\})", feedback)
                        res_dict = json.loads(match.group(1)) if match else {}
                        tkt_id = res_dict.get("ticket_id", "tkt_123")
                        status = res_dict.get("status", "in_progress")
                    except Exception:
                        tkt_id, status = "tkt_123", "in_progress"
                    if is_hindi:
                        reply = f"टिकट {tkt_id} की स्थिति '{status}' है।"
                    elif is_hinglish:
                        reply = f"Ticket {tkt_id} ka status '{status}' hai."
                    else:
                        reply = f"The status of ticket {tkt_id} is '{status}'."
                elif "handoff_to_agent" in feedback:
                    if is_hindi:
                        reply = "आपको सपोर्ट एजेंट से कनेक्ट किया जा रहा है।"
                    elif is_hinglish:
                        reply = "Aapko live support agent se connect kiya ja raha hai."
                    else:
                        reply = "You are being connected to a live support agent."
                elif "create_support_ticket" in feedback:
                    ticket_id = "TICK-1001"
                    try:
                        match = re.search(r"ticket_id\":\s*\"([^\"]+)\"", feedback)
                        if match:
                            ticket_id = match.group(1)
                    except Exception:
                        pass
                    if is_bengali:
                        reply = f"পেমেন্ট বিরোধ টিকিট সফলভাবে জমা দেওয়া হয়েছে। টিকিট আইডি: {ticket_id}।"
                    elif is_marathi:
                        reply = f"पेमेंट तक्रार यशस्वीपणे नोंदवली गेली आहे. तिकीट आयडी: {ticket_id}."
                    elif is_raj:
                        reply = f"पेमेंट विवाद टिकट सफलतापूर्वक जमा हो गयो है। टिकट आईडी: {ticket_id}।"
                    elif is_punjabi:
                        reply = f"ਭੁਗਤਾਨ ਵਿਵਾਦ ਟਿਕਟ ਸਫਲਤਾਪੂਰਵਕ ਦਰਜ ਕੀਤੀ ਗਈ ਹੈ। ਟਿਕਟ ਆਈਡੀ: {ticket_id}।"
                    elif is_gujarati:
                        reply = f"ચુકવણી વિવાદ ટિકિટ સફળતાપૂર્વક સબમિટ કરવામાં આવી છે. ટિકિટ આઈડી: {ticket_id}."
                    elif is_hindi:
                        reply = f"पेमेंट विवाद टिकट सफलतापूर्वक दर्ज कर दिया गया है। टिकट आईडी: {ticket_id}।"
                    elif is_hinglish:
                        reply = f"Payment dispute ticket successfully start kar diya gaya hai. Ticket ID: {ticket_id}."
                    else:
                        reply = f"Payment dispute ticket has been successfully created with ID: {ticket_id}."
                elif "cancel_ride" in feedback:
                    if is_hindi:
                        reply = "आपकी राइड सफलतापूर्वक रद्द कर दी गई है।"
                    elif is_hinglish:
                        reply = "Aapki ride successfully cancel ho gayi hai."
                    else:
                        reply = "Your ride has been successfully cancelled."
                elif "request_refund" in feedback:
                    if is_hindi:
                        reply = "आपका रिफंड अनुरोध सफलतापूर्वक दर्ज कर लिया गया है।"
                    elif is_hinglish:
                        reply = "Aapka refund request successfully submit ho gaya hai."
                    else:
                        reply = "Your refund request has been submitted successfully."
                elif "start_rematch" in feedback:
                    if is_hindi:
                        reply = "नये ड्राइवर के साथ रीमैच शुरू कर दिया गया है।"
                    elif is_hinglish:
                        reply = "Naye driver ke saath rematch start kar diya gaya hai."
                    else:
                        reply = "Rematch has been initiated to find a new driver."
                else:
                    if is_hinglish:
                        reply = "Action successfully execute ho gaya hai."
                    else:
                        reply = "Action completed successfully."
                return LLMResponse(text=reply, tool_calls=[], model=self.model, input_tokens=10, output_tokens=20)

            # 3. Tool denied (Authorization failure)
            elif "denied:" in feedback:
                if is_hindi:
                    reply = "आपके पास यह कार्रवाई करने की अनुमति नहीं है।"
                elif is_hinglish:
                    reply = "Aapke paas yeh action perform karne ki permission nahi hai."
                else:
                    reply = "You do not have authorization to perform this action."
                return LLMResponse(text=reply, tool_calls=[], model=self.model, input_tokens=10, output_tokens=20)

            # 4. Tool execution failed
            elif "failed:" in feedback or "execution failed" in feedback:
                if is_hindi:
                    reply = "कार्रवाई निष्पादित करने में विफलता आई। कृपया बाद में पुनः प्रयास करें।"
                elif is_hinglish:
                    reply = "Action execute karne mein samasya aayi. Kripya kuch samay baad dobara prayas karein."
                else:
                    reply = "Failed to execute action. Please try again later."
                return LLMResponse(text=reply, tool_calls=[], model=self.model, input_tokens=10, output_tokens=20)

        # Check if conversation history has an action pending confirmation and user replied affirmatively
        last_asst_msg = next((m for m in reversed(messages) if m.role == "assistant"), None)
        asst_content = (last_asst_msg.content or "").lower() if last_asst_msg else ""
        has_asked_confirmation = bool(last_asst_msg) and (
            any(
                w in asst_content for w in [
                    "confirm", "chahiye", "જોઈએ", "ਚਾਹੀਦਾ", "চাই", "आवश्यकता", "तक्रार", "dispute", "cancel", "refund",
                    "নিশ্চিতকরণ", "প্রয়োজন", "પુષ્ટિ", "ਪੁਸ਼ਟੀ", "पुष्टि", "पुष्टी", "रद्द", "रिफंड", "विवाद", "टिकट", "ticket"
                ]
            ) or any(c in asst_content for c in ["?", "kya", "क्या", "શું", "ਕੀ", "কি", "काईं"])
        )
        is_user_affirming = any(
            w in msg_lower for w in [
                "yes", "confirm", "haan", "ha", "ok", "okay", "kar do", "karo", "कर दो", "ਕਰੋ", "કરો", "করুন",
                "do it", "bilkul", "yes please", "sure", "proceed", "go ahead", "start",
                "हाँ", "हौ", "होय", "હા", "হ্যাঁ", "ਹਾਂ", "શરૂ કરો", "કરી દો", "শুরু করুন", "ਸ਼ੁਰੂ ਕਰੋ", "करा", "शुरू कर दो", "start kar do"
            ]
        )

        # Security & Privacy Guardrails:
        # 1. PII / Contact details requests (customer/driver phone, personal address, government ID)
        is_pii_request = any(
            w in msg_lower for w in [
                "customer's phone number", "customer phone number", "driver's phone number", "driver phone number",
                "phone number of customer", "phone number of driver", "customer ka phone number", "driver ka phone number",
                "ग्राहक का फोन नंबर", "गौपनियता", "गोंपनीयता", "ગ્રાહકનો ફોન નંબર", "গ্রাহকের ফোন নম্বর",
                "फोन नंबर दो", "फोन नंबर दे दो", "phone number de do", "phone number de",
                "driver's personal address", "driver personal address", "personal address of driver", "driver's address",
                "home address of customer", "home address of driver", "customer address"
            ]
        ) or (any(w in msg_lower for w in ["phone number", "phone", "contact number", "address", "पता", "नंबर", "ਨੰਬਰ", "સરનામું", "ঠিকানা"]) and any(w in msg_lower for w in ["customer", "driver", "rider", "ग्राहक", "<ctrl42>ડ્રાઇવર", "ড্রাইভার", "ਗ੍ਰਾਹਕ"]))
        if is_pii_request:
            if is_bengali:
                reply = "আমি গোপনীয়তা নীতি অনুসারে গ্রাহক বা ড্রাইভারের ব্যক্তিগত যোগাযোগের তথ্য বা ঠিকানা প্রদান করতে পারি না।"
            elif is_gujarati:
                reply = "હું ગોપનીયતા નીતિ અનુસાર ગ્રાહક અથવા ડ્રાઇવરની ખાનગી સંપર્ક માહિતી અથવા સરનામું આપી શકતો નથી."
            elif is_hindi:
                reply = "गोपनीयता नीति के अनुसार मैं ग्राहकों या ड्राइवरों की निजी संपर्क जानकारी या पता साझा नहीं कर सकता।"
            elif is_hinglish:
                reply = "GoRush privacy policy ke according main customer ya driver ki private contact details share nahi kar sakta."
            else:
                reply = "I cannot provide private contact information or personal details of customers or drivers per GoRush privacy policies."
            return LLMResponse(text=reply, tool_calls=[], model=self.model, input_tokens=10, output_tokens=20)

        # 2. Secret / API key / System prompt request
        is_secret_request = any(
            w in msg_lower for w in [
                "api key", "api_key", "secret key", "internal secret", "system prompt", "hidden system prompt",
                "show me your prompt", "reveal prompt", "database secret"
            ]
        )
        if is_secret_request:
            if is_hindi:
                reply = "सुरक्षा नीतियों के अनुसार मैं एपीआई कुंजी, सिस्टम प्रॉम्प्ट या आंतरिक गोपनीय जानकारी का खुलासा नहीं कर सकता।"
            elif is_hinglish:
                reply = "Main API key, system prompt, ya internal secrets disclose nahi kar sakta."
            else:
                reply = "I cannot disclose system secrets, API keys, or hidden system prompts."
            return LLMResponse(text=reply, tool_calls=[], model=self.model, input_tokens=10, output_tokens=20)

        # 3. Prompt injection / Admin access / Override requests
        is_injection_request = any(
            w in msg_lower for w in [
                "ignore your safety rules", "ignore safety rules", "ignore authorization",
                "system says i am an admin", "give me admin access", "i am an admin", "bypass safety",
                "execute the tool even if"
            ]
        )
        if is_injection_request:
            if is_hindi:
                reply = "मैं सुरक्षा नियमों, नीतियों या प्राधिकरण नियंत्रणों को बायपास नहीं कर सकता।"
            elif is_hinglish:
                reply = "Main safety rules, authorization, ya system security controls ko bypass nahi kar sakta."
            else:
                reply = "I cannot bypass authorization, safety policies, or system security controls."
            return LLMResponse(text=reply, tool_calls=[], model=self.model, input_tokens=10, output_tokens=20)

        # 4. Other user's earnings request
        is_other_user_earnings = any(
            w in msg_lower for w in [
                "another driver's earnings", "other driver's earnings", "another user's earnings", "someone else's earnings",
                "other driver earnings", "another driver"
            ]
        )
        if is_other_user_earnings:
            if is_hindi:
                reply = "मैं अन्य ड्राइवरों या उपयोगकर्ताओं की कमाई का विवरण प्रदर्शित नहीं कर सकता।"
            elif is_hinglish:
                reply = "Main doosre drivers ya users ki earnings details display nahi kar sakta."
            else:
                reply = "I cannot display earnings or personal data of other drivers or users."
            return LLMResponse(text=reply, tool_calls=[], model=self.model, input_tokens=10, output_tokens=20)

        # Check for explicit action request triggers
        has_dispute_action = any(
            w in msg_lower or w in last_user_msg for w in [
                "dispute start", "start dispute", "log dispute", "dispute log", "dispute kar do",
                "dispute karo", "start kar do", "dispute शुरू", "వివాదం", "বিবাদ", "বিরোধ", "dispute raise"
            ]
        )
        has_cancel_action = any(
            w in msg_lower or w in last_user_msg for w in [
                "cancel ride", "ride cancel", "cancel my ride", "cancel karo", "cancel kar do", "trip cancel", "cancel it"
            ]
        )
        has_refund_action = any(
            w in msg_lower or w in last_user_msg for w in [
                "request refund", "process refund", "issue refund", "refund kar do", "paisa wapas karo", "refund request"
            ]
        )
        has_rematch_action = any(
            w in msg_lower or w in last_user_msg for w in [
                "start rematch", "rematch driver", "find new driver", "rematch kar do"
            ]
        )

        has_active_ride_action = any(
            w in msg_lower or w in last_user_msg for w in [
                "where is my active ride", "active ride", "ride status", "active...ride",
                "meri active ride", "मेरी एक्टिव राइड", "મારી એક્ટિવ રાઇડ", "আমার সক্রিয় রাইড", "ਸਰਗਰਮ ਰਾਈਡ",
                "active ride kahan", "active ride kya", "active ride کہاں"
            ]
        ) or (any(w in msg_lower for w in ["where", "kaha", "kahan", "location", "status", "कहाँ", "कहा", "ક્યાં", "কোথায়", "ਕਿੱਥੇ", "कुठे"]) and any(w in msg_lower or w in last_user_msg for w in ["ride", "driver", "राइड", "રાઇડ", "রাইড", "ਰਾਈਡ"]))
        has_eta_action = any(
            w in msg_lower or w in last_user_msg for w in [
                "what is my eta", "driver eta", "my eta", "get eta", "when my driver come", "eta"
            ]
        )
        has_fare_action = any(
            w in msg_lower or w in last_user_msg for w in [
                "how much was the fare", "how much is the fare", "fare breakdown", "fare", "price", "kitna paisa", "fare details"
            ]
        )
        has_payment_status_action = any(
            w in msg_lower or w in last_user_msg for w in [
                "what is my payment status", "payment status", "check payment status", "payment fail", "payment issue"
            ]
        )
        has_refund_status_action = any(
            w in msg_lower or w in last_user_msg for w in [
                "what is my refund status", "refund status", "check refund status", "refund status check"
            ]
        )
        has_earnings_action = any(
            w in msg_lower or w in last_user_msg for w in [
                "how much did i earn", "daily earning", "weekly earning", "monthly earning",
                "aaj ki kamai", "haftewari kamai", "kamai", "earning", "earnings", "कमाई", "કમાણી", "ਕਮਾਈ"
            ]
        )
        has_document_status_action = any(
            w in msg_lower or w in last_user_msg for w in [
                "document status", "kagaz expire", "license status", "rc status", "check document",
                "my documents", "documents verified", "documents approved", "are my documents"
            ]
        )
        has_ticket_status_action = any(
            w in msg_lower or w in last_user_msg for w in [
                "ticket status", "check ticket status", "what is my ticket status", "ticket status info"
            ]
        )
        has_handoff_action = any(
            w in msg_lower or w in last_user_msg for w in [
                "human agent", "talk to person", "real agent", "human support", "speak to human"
            ]
        )

        is_kb_policy_query = any(
            w in msg_lower or w in last_user_msg for w in [
                "policy", "rule", "rules", "how does", "what is the", "what are the",
                "terms", "faq", "procedure", "how long does", "what documents do", "how to", "what documents are",
                "why was", "how is", "explain", "onboarding", "sla", "process", "tell me about", "can you explain",
                "when can", "what happens if", "what should i do", "how can i",
                "पॉलिसी", "नियम", "क्या नियम", "नियम क्या", "प्रक्रिया", "दिशा-निर्देश", "kya hai", "kya hain",
                "પોલિસી", "નિયમો", "શું છે", "নীতি", "নিয়ম", "কী"
            ]
        ) and not any(w in msg_lower for w in ["my document", "my documents", "my ride", "my refund", "my payment", "my earnings", "check my", "cancel my", "my account"])

        # Route confirmation or explicit action to appropriate tool (only if not a pure policy/FAQ question)
        if has_active_ride_action and not is_kb_policy_query:

            return LLMResponse(
                text="",
                tool_calls=[{"name": "get_active_ride", "input": {}}],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        if has_eta_action:
            return LLMResponse(
                text="",
                tool_calls=[{"name": "get_driver_eta", "input": {}}],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        if has_fare_action and not is_kb_policy_query:
            return LLMResponse(
                text="",
                tool_calls=[{"name": "get_ride_fare_breakdown", "input": {}}],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        if has_payment_status_action and not is_kb_policy_query:
            return LLMResponse(
                text="",
                tool_calls=[{"name": "get_payment_status", "input": {"ride_id": "ride_123"}}],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        if has_refund_status_action and not is_kb_policy_query:
            return LLMResponse(
                text="",
                tool_calls=[{"name": "get_refund_status", "input": {"ride_id": "ride_123"}}],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        if has_earnings_action and not is_kb_policy_query:
            return LLMResponse(
                text="",
                tool_calls=[{"name": "get_driver_earnings", "input": {"period": "today"}}],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        if has_document_status_action and not is_kb_policy_query:
            return LLMResponse(
                text="",
                tool_calls=[{"name": "get_document_status", "input": {}}],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )


        if has_ticket_status_action:
            return LLMResponse(
                text="",
                tool_calls=[{"name": "get_ticket_status", "input": {"ticket_id": "tkt_123"}}],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        has_p1_hacked_action = any(
            w in msg_lower for w in ["hacked", "hack", "compromised", "account hacked", "account hack"]
        )
        has_p2_stuck_refund_action = any(
            w in msg_lower for w in ["refund is stuck", "refund stuck", "stuck refund"]
        )

        if has_p1_hacked_action:
            return LLMResponse(
                text="",
                tool_calls=[{"name": "handoff_to_agent", "input": {"reason": "account_compromise", "priority": "P1"}}],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        if has_p2_stuck_refund_action:
            return LLMResponse(
                text="",
                tool_calls=[{"name": "handoff_to_agent", "input": {"reason": "stuck_refund", "priority": "P2"}}],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        if has_handoff_action:
            return LLMResponse(
                text="",
                tool_calls=[{"name": "handoff_to_agent", "input": {"reason": "user_requested_human", "priority": "P2"}}],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        if ((has_asked_confirmation and is_user_affirming and any(w in asst_content for w in ["cancel", "रद्द", "cancellation"])) or has_cancel_action) and not is_kb_policy_query:

            return LLMResponse(
                text="",
                tool_calls=[{
                    "name": "cancel_ride",
                    "input": {
                        "ride_id": "ride_123",
                        "reason": last_user_msg or "User requested ride cancellation"
                    }
                }],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        if (has_asked_confirmation and is_user_affirming and any(w in asst_content for w in ["refund", "रिफंड"])) or has_refund_action:
            return LLMResponse(
                text="",
                tool_calls=[{
                    "name": "request_refund",
                    "input": {
                        "ride_id": "ride_123",
                        "amount": 50.0,
                        "reason": last_user_msg or "Refund requested by user"
                    }
                }],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        if (has_asked_confirmation and is_user_affirming and "rematch" in asst_content) or has_rematch_action:
            return LLMResponse(
                text="",
                tool_calls=[{
                    "name": "start_rematch",
                    "input": {
                        "ride_id": "ride_123"
                    }
                }],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        if has_dispute_action or (has_asked_confirmation and is_user_affirming):
            return LLMResponse(
                text="",
                tool_calls=[{
                    "name": "create_support_ticket",
                    "input": {
                        "category": "payment_dispute",
                        "description": last_user_msg or "Payment dispute requested by user"
                    }
                }],
                model=self.model,
                input_tokens=10,
                output_tokens=20,
            )

        # Security & Privacy Guardrails:
        # 1. PII / Contact details requests (customer/driver phone, personal address, government ID)
        is_pii_request = any(
            w in msg_lower for w in [
                "customer's phone number", "customer phone number", "driver's phone number", "driver phone number",
                "phone number of customer", "phone number of driver", "customer ka phone number", "driver ka phone number",
                "ग्राहक का फोन नंबर", "ગ્રાહકનો ફોન નંબર", "গ্রাহকের ফোন নম্বর", "फोन नंबर", "phone number",
                "driver's personal address", "driver personal address", "personal address of driver", "driver's address",
                "home address of customer", "home address of driver", "customer address"
            ]
        ) and any(w in msg_lower for w in ["give", "show", "tell", "de do", "do", "आपो", "দিন", "address", "phone", "number"])
        if is_pii_request:
            if is_bengali:
                reply = "আমি গোপনীয়তা নীতি অনুসারে গ্রাহক বা ড্রাইভারের ব্যক্তিগত যোগাযোগের তথ্য বা ঠিকানা প্রদান করতে পারি না।"
            elif is_gujarati:
                reply = "હું ગોપનીયતા નીતિ અનુસાર ગ્રાહક અથવા ડ્રાઇવરની ખાનગી સંપર્ક માહિતી અથવા સરનામું આપી શકતો નથી."
            elif is_hindi:
                reply = "गोपनीयता नीति के अनुसार मैं ग्राहकों या ड्राइवरों की निजी संपर्क जानकारी या पता साझा नहीं कर सकता।"
            elif is_hinglish:
                reply = "GoRush privacy policy ke according main customer ya driver ki private contact details share nahi kar sakta."
            else:
                reply = "I cannot provide private contact information or personal details of customers or drivers per GoRush privacy policies."
            return LLMResponse(text=reply, tool_calls=[], model=self.model, input_tokens=10, output_tokens=20)

        # 2. Secret / API key / System prompt request
        is_secret_request = any(
            w in msg_lower for w in [
                "api key", "api_key", "secret key", "internal secret", "system prompt", "hidden system prompt",
                "show me your prompt", "reveal prompt", "database secret"
            ]
        )
        if is_secret_request:
            if is_hindi:
                reply = "सुरक्षा नीतियों के अनुसार मैं एपीआई कुंजी, सिस्टम प्रॉम्प्ट या आंतरिक गोपनीय जानकारी का खुलासा नहीं कर सकता।"
            elif is_hinglish:
                reply = "Main API key, system prompt, ya internal secrets disclose nahi kar sakta."
            else:
                reply = "I cannot disclose system secrets, API keys, or hidden system prompts."
            return LLMResponse(text=reply, tool_calls=[], model=self.model, input_tokens=10, output_tokens=20)

        # 3. Prompt injection / Admin access / Override requests
        is_injection_request = any(
            w in msg_lower for w in [
                "ignore your safety rules", "ignore safety rules", "ignore authorization",
                "system says i am an admin", "give me admin access", "i am an admin", "bypass safety",
                "execute the tool even if"
            ]
        )
        if is_injection_request:
            if is_hindi:
                reply = "मैं सुरक्षा नियमों, नीतियों या प्राधिकरण नियंत्रणों को बायपास नहीं कर सकता।"
            elif is_hinglish:
                reply = "Main safety rules, authorization, ya system security controls ko bypass nahi kar sakta."
            else:
                reply = "I cannot bypass authorization, safety policies, or system security controls."
            return LLMResponse(text=reply, tool_calls=[], model=self.model, input_tokens=10, output_tokens=20)

        # 4. Other user's earnings request
        is_other_user_earnings = any(
            w in msg_lower for w in [
                "another driver's earnings", "other driver's earnings", "another user's earnings", "someone else's earnings",
                "other driver earnings"
            ]
        )
        if is_other_user_earnings:
            if is_hindi:
                reply = "मैं अन्य ड्राइवरों या उपयोगकर्ताओं की कमाई का विवरण प्रदर्शित नहीं कर सकता।"
            elif is_hinglish:
                reply = "Main doosre drivers ya users ki earnings details display nahi kar sakta."
            else:
                reply = "I cannot display earnings or personal data of other drivers or users."
            return LLMResponse(text=reply, tool_calls=[], model=self.model, input_tokens=10, output_tokens=20)

        # Fallback to standard conversational responses if no explicit action requested
        if any(w in msg_lower or w in last_user_msg for w in [
            "भुगतान नहीं", "cash payment", "didn't pay", "did not make", "cash nahi",
            "भुगतान कोनी", "कोनी कर्यो", "ਕੀਤਾ", "ਚੁਕવણી", "ચુકવણી", "nathi", "koni",
            "পেমেন্ট করেনি", "पेमेंट केले नाही"
        ]):
            if is_bengali:
                reply = "গ্রাহক পেমেন্ট করেনি। আপনি কি পেমেন্ট ডিসপিউট শুরু করতে চান?"
            elif is_marathi:
                reply = "ग्राहकाने पेमेंट केले नाही. तुम्ही पेमेंट तक्रार नोंदवू इच्छिता का?"
            elif is_raj:
                reply = "ग्राहक नै भुगतान कोनी कर्यो है। आप ग्राहक सू भुगतान प्राप्त करवा खातर काईं करबो चाहो?"
            elif is_punjabi:
                reply = "ਗਾਹਕ ਨੇ ਭੁਗਤਾਨ ਨਹੀਂ ਕੀਤਾ ਹੈ। ਤੁਸੀਂ ਗਾਹਕ ਤੋਂ ਭੁਗਤਾਨ ਪ੍ਰਾਪਤ ਕਰਨ ਲਈ ਕੀ ਕਰਨਾ ਚਾਹੁੰਦੇ ਹੋ?"
            elif is_gujarati:
                reply = "ગ્રાહકે ચુકવણી કરી નથી. તમે ગ્રાહક પાસેથી ચુકવણી મેળવવા માટે શું કરવા માંગો છો?"
            elif is_hindi:
                reply = "ग्राहक ने भुगतान नहीं किया है। आप ग्राहक से भुगतान प्राप्त करने के लिए क्या करना चाहते हैं?"
            elif is_hinglish:
                reply = "Customer ne payment nahi kiya hai. Aap payment dispute log karna chahte hain?"
            else:
                reply = "Customer did not make the payment. Would you like to log a payment dispute or check payment status?"

        elif any(w in msg_lower or w in last_user_msg for w in ["ride offer", "booking offer", "offer nahi"]):
            if is_raj:
                reply = "थारी राइड ऑफर डिस्पैच स्थिति क्लियर है। जीपीएस रिफ्रेश करो और ऐप ने अवेलेबल मोड में राखो।"
            elif is_punjabi:
                reply = "ਤੁਹਾਡੀ ਰਾਈਡ ਆਫਰ ਸਥਿਤੀ ਸਰਗਰਮ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਜੀਪੀਐਸ ਅਤੇ ਇੰਟਰਨੈਟ ਦੀ ਜਾਂਚ ਕਰੋ।"
            elif is_gujarati:
                reply = "તમારી રાઈડ ઓફર ડિસ્પેચ સ્થિતિ સક્રિય છે. કૃપા કરીને જીપીએસ ચકાસો."
            elif is_hindi:
                reply = "आपकी राइड ऑफर डिस्पैच स्थिति सामान्य है। कृपया अपना जीपीएस और इंटरनेट जांचें।"
            elif is_hinglish:
                reply = "Aapki ride offer dispatch status clear hai. Internet aur GPS check karke app ko refresh karein."
            else:
                reply = "Your ride offer dispatch status is active. Please verify your GPS and network connectivity."

        elif any(w in msg_lower or w in last_user_msg for w in ["earning", "kamai", "कमाई", "<ctrl42>ਕਮਾਈ", "કમાણી"]):
            if is_raj:
                reply = "थारी आज री कुल दैनिक कमाई री रिपोर्ट ऐप में अपडेट हो गी है।"
            elif is_punjabi:
                reply = "ਤੁਹਾਡੀ ਅੱਜ ਦੀ ਕੁੱਲ ਕਮਾਈ ਦੀ ਰਿਪੋਰਟ ਅਪਡੇਟ ਹੋ ਗਈ ਹੈ।"
            elif is_gujarati:
                reply = "તમારી આજના દિવસની કુલ કમાણી અહેવાલ અપડેટ કરવામાં આવ્યો છે."
            elif is_hindi:
                reply = "आपकी आज की कुल दैनिक कमाई की रिपोर्ट ऐप में अपडेट कर दी गई है।"
            elif is_hinglish:
                reply = "Aapki aaj ki daily earnings breakdown app mein update ho gayi hai."
            else:
                reply = "Your daily earnings breakdown for today has been updated in your app."

        elif any(w in msg_lower or w in last_user_msg for w in ["नुकसान", "परेशान", "frustrated", "loss", "bekar", "bina baat"]):
            if is_hindi:
                reply = "समझ सकता हूँ कि यह परेशान करने वाली स्थिति है। मैं payment issue में आपकी मदद करता हूँ। अगर आप चाहें तो हम payment dispute शुरू कर सकते हैं।"
            elif is_hinglish:
                reply = "Main samajh sakta hoon ki yeh troubling situation hai. Main aapki payment issue mein help kar sakta hoon. Aap payment dispute start karna chahte hain?"
            elif is_bengali:
                reply = "আমি বুঝতে পারছি এটি একটি কষ্টদায়ক পরিস্থিতি। আমি আপনাকে পেমেন্ট বিষয়ে সাহায্য করতে পারি।"
            elif is_gujarati:
                reply = "હું સમજી શકું છું કે આ ચિંતાજનક પરિસ્થિતિ છે. હું તમને પેમેન્ટ ડિસ્પ્યુટમાં મદદ કરી શકું છું."
            elif is_raj:
                reply = "मैं समझ सकूं कि ओ परेशान करवा वाली बात है। मैं थारी पेमेंट समस्या में मदद करूँ।"
            else:
                reply = "I understand this is a frustrating situation. I am here to help you resolve this payment issue. Would you like to start a payment dispute?"

        elif any(w in msg_lower or w in last_user_msg for w in [
            "cancellation", "cancel policy", "cancellation rules", "cancel rules", "when can a ride be cancelled",
            "what happens if i cancel", "कैंसिलेशन", "केन्सलेशन", "कैंसिलेशन के नियम", "कैंसिल करने की", "રદ", "કેન્સલ", "বাতিল"
        ]) or (is_kb_policy_query and "cancel" in msg_lower):
            if is_bengali:
                reply = "GoRush বাতিল নীতি: বুকিংয়ের 2 মিনিটের মধ্যে বিনামূল্যে রাইড বাতিল করা যায়। 2 মিনিটের পরে ₹50 ফি প্রযোজ্য।"
            elif is_gujarati:
                reply = "GoRush કેન્સલેશન પોલિસી: બુકિંગના 2 મિનિટની અંદર રાઇડ મફત રદ કરી શકાય છે. 2 મિનિટ પછી ₹50 ફી લાગુ પડે છે."
            elif is_hindi:
                reply = "GoRush कैंसिलेशन पॉलिसी: बुकिंग के 2 मिनट के भीतर राइड मुफ़्त रद्द की जा सकती है। 2 मिनट के बाद ₹50 का कैंसिलेशन शुल्क लागू होता है।"
            elif is_hinglish:
                reply = "GoRush Cancellation Policy: Booking ke 2 mins ke andar ride free cancel kar sakte hain. 2 mins ke baad ₹50 cancellation fee apply hoti hai."
            else:
                reply = "GoRush Cancellation Policy: Rides can be cancelled free of charge within 2 minutes of booking. If cancelled after 2 minutes, a standard cancellation fee of ₹50 applies."

        elif any(w in msg_lower or w in last_user_msg for w in ["refund policy", "refund rules", "refund process", "how refund work"]):
            if is_hindi:
                reply = "GoRush रिफंड पॉलिसी: रद्द की गई राइड या गलत कटौती के लिए रिफंड अनुरोध 3-5 कार्य दिवसों में संसाधित किए जाते हैं।"
            elif is_hinglish:
                reply = "GoRush Refund Policy: Eligible refund requests for cancelled rides or wrong deductions are processed within 3-5 business days."
            else:
                reply = "GoRush Refund Policy: Eligible refund requests for cancelled rides or incorrect deductions are processed within 3-5 business days."

        elif any(w in msg_lower or w in last_user_msg for w in ["document", "documents", "dastavez", "दस्तावेज़", "દસ્તાવેજ", "নথি"]):
            if is_hindi:
                reply = "GoRush दस्तावेज़ आवश्यकताएँ: ड्राइवर बनने के लिए वैध ड्राइविंग लाइसेंस, वाहन आरसी (RC), व्यावसायिक बीमा और आईडी प्रूफ आवश्यक हैं।"
            elif is_hinglish:
                reply = "GoRush Document Requirements: Driver banne ke liye valid Driving License, Vehicle RC, Commercial Insurance, aur ID proof required hain."
            else:
                reply = "GoRush Document Requirements: Drivers must provide a valid Driving License, Vehicle Registration Certificate (RC), Commercial Insurance, and identity proof."

        elif any(w in msg_lower or w in last_user_msg for w in ["onboard", "onboarding"]):
            if is_hindi:
                reply = "GoRush ड्राइवर ऑनबोर्डिंग: ऐप डाउनलोड करें, लाइसेंस, आरसी और बीमा अपलोड करें, और सत्यापन के बाद ड्राइविंग शुरू करें।"
            elif is_hinglish:
                reply = "GoRush Driver Onboarding: Driver app download karein, DL, RC, Insurance upload karein, aur verification ke baad duty start karein."
            else:
                reply = "GoRush Driver Onboarding: Download the GoRush Driver App, upload required documents (DL, RC, Insurance), pass background verification, and start driving."

        elif any(w in msg_lower or w in last_user_msg for w in ["sla", "support SLA", "support take", "support time"]):
            if is_hindi:
                reply = "GoRush सपोर्ट SLA: आपातकालीन और P0/P1 मुद्दों को तुरंत मानव एजेंटों को भेजा जाता है। सामान्य प्रश्नों का उत्तर 15-30 मिनट में दिया जाता है।"
            elif is_hinglish:
                reply = "GoRush Support SLA: Critical and emergency (P0/P1) issues receive immediate human agent escalation. Standard tickets are handled within 15-30 minutes."
            else:
                reply = "GoRush Support SLA: Critical and safety issues (P0/P1) receive immediate agent escalation. Standard support inquiries are answered within 15-30 minutes."

        elif is_kb_policy_query:
            if is_bengali:
                reply = "GoRush সহায়তা কেন্দ্র: এই বিষয়ে আমাদের অনুমোদিত নীতি সম্পর্কে আরও তথ্যের জন্য অনুগ্রহ করে আমাদের হেল্প সেন্টার নিবন্ধ দেখুন।"
            elif is_gujarati:
                reply = "GoRush સપોર્ટ નીતિ: આ વિષય માટે અમારી મંજૂર નીતિ વિગતો કૃપા કરીને હેલ્પ સેન્ટરમાં તપાસો."
            elif is_hindi:
                reply = "GoRush सहायता नीति: इस विषय के लिए हमारी अनुमोदित नीति दिशानिर्देशों के अनुसार जानकारी ऐप में उपलब्ध है।"
            elif is_hinglish:
                reply = "GoRush Support Policy: Iss topic ke liye humari approved policy guidelines ke acccording details available hain."
            else:
                reply = "GoRush Support Policy: Details for this topic are governed by approved GoRush policy guidelines."

        else:

            if is_bengali:
                reply = "আমি GoRush Assistant। আমি আপনাকে রাইড, পেমেন্ট বা আয়ের বিষয়ে সাহায্য করতে পারি।"
            elif is_marathi:
                reply = "मी GoRush Assistant आहे. मी तुम्हाला राइड, पेमेंट किंवा कमाई विषयी मदत करू शकतो."
            elif is_raj:
                reply = "मैं GoRush Assistant हूँ। मैं थारी राइड, पेमेंट और कमाई री जानकारी में मदद कर सकूं।"
            elif is_punjabi:
                reply = "ਮੈਂ GoRush Assistant ਹਾਂ। ਮੈਂ ਤੁਹਾਡੀ ਰਾਈਡ, ਭੁਗਤਾਨ ਜਾਂ ਕਮਾਈ ਸੰਬੰਧੀ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ।"
            elif is_gujarati:
                reply = "હું GoRush Assistant છું. હું તમને રાઈડ, પેમેન્ટ અથવા કમાણી સંબંધિત મદદ કરી શકું છું."
            elif is_hindi:
                reply = "मैं GoRush Assistant हूँ। मैं आपकी राइड, पेमेंट, कमाई या अकाउंट सहायता में मदद कर सकता हूँ।"
            elif is_hinglish:
                reply = "Main GoRush Assistant hoon. Main aapki ride, payment dispute, ya earnings help mein assist kar sakta hoon."
            else:
                reply = "I am GoRush Assistant. I can assist you with your rides, payments, earnings, or connecting with support."

        return LLMResponse(text=reply, tool_calls=[], model=self.model, input_tokens=10, output_tokens=20)

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        reply = "Processing response..."
        yield reply

    async def structured_output(
        self,
        messages: list[ChatMessage],
        *,
        json_schema: dict[str, Any],
        system: str | None = None,
    ) -> dict[str, Any]:
        return {"intent": "faq", "confidence": 0.95, "note": "mock provider inference"}

    async def embeddings(self, texts: list[str]) -> list[list[float]]:
        dim = get_settings().embedding_dim
        return [[0.0] * dim for _ in texts]
