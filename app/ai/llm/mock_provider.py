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
                if "create_support_ticket" in feedback:
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

        # Route confirmation or explicit action to appropriate tool
        if (has_asked_confirmation and is_user_affirming and any(w in asst_content for w in ["cancel", "रद्द", "cancellation"])) or has_cancel_action:
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
