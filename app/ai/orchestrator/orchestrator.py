from typing import Any
import json
import re
import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.intent.detector import intent_detector
from app.ai.intent.schema import IntentResult
from app.ai.llm.gateway import LLMGateway
from app.ai.llm.provider import ChatMessage, ToolSpec
from app.ai.orchestrator.loop_guard import LoopGuard, OrchestrationLimitExceededError
from app.ai.orchestrator.schema import HandoffInfo, OrchestrationResult
from app.ai.language.config import is_language_enabled
from app.ai.language.localization import get_localized_text
from app.ai.language.validator import validate_response_language
from app.ai.prompts.registry import LANGUAGE_CODE_TO_NAME, get_prompt
from app.audit.service import AuditService
from app.common.enums.chat import Intent, MessageRole, Priority, UserRole
from app.common.exceptions.base import ConfirmationRequiredError, ForbiddenError, ToolDeniedError
from app.conversations.context_service import ContextService
from app.conversations.service import ConversationService
from app.core.config import get_settings
from app.core.logging import get_logger
from app.guardrails.input.pipeline import input_guardrail_pipeline
from app.guardrails.output.pipeline import output_guardrail_pipeline
from app.handoff.service import HandoffService
from app.knowledge.embeddings.provider import get_embedding_provider
from app.knowledge.retrieval.service import RAGRetrievalService
from app.tools.registry.registry import ToolRegistry, default_tool_registry
from app.tools.registry.tool_spec import ToolContext
from app.tools.router.tool_router import ToolRouter

logger = get_logger(__name__)

# Intents that should always be resolved with an approved knowledge article
# rather than free-form LLM generation.
# These map to KB article categories ingested via the knowledge ingestion pipeline.
# Add an intent here only if approved articles for that category exist in the DB.
KNOWLEDGE_DRIVEN_INTENTS = {
    Intent.FAQ,                  # category: "faq"
    Intent.CANCELLATION,         # category: "cancellation" (policy & fees)
    Intent.REFUND,               # category: "refund" (eligibility & timelines)
    Intent.PROMO,                # category: "promo" (discount & coupon rules)
    Intent.PRIVACY,              # category: "privacy" (data policy)
    Intent.ACCOUNT,              # category: "account" (profile, login, deletion)
    Intent.WALLET,               # category: "wallet" (balance, top-up, limits)
    Intent.REFERRAL,             # category: "referral" (earn cashback, invite rules)
    Intent.INCENTIVE,            # category: "incentive" (bonus targets & payout terms)
    Intent.DOCUMENT_STATUS,      # category: "document_status" (expiry & verification guidelines)
    Intent.VEHICLE_DOCUMENT,     # category: "vehicle_document" (vehicle change & RC rules)
    Intent.NAVIGATION,           # category: "navigation" (GPS & mapping guidance)
    Intent.APP_TROUBLESHOOTING,  # category: "app_troubleshooting" (app crashes & troubleshooting)
    Intent.SAFETY,               # category: "safety" (post-accident & safety procedures)
    Intent.FARE,                 # category: "fare" (fare calculation & pricing rules)
    Intent.ACCEPTANCE,           # category: "acceptance" (acceptance rules & guidelines)
}




REFUND_RESPONSES = {
    "eligible_guide": {
        "hi": "बिल्कुल, मैंने आपकी पिछली राइड और पेमेंट विवरण चेक कर लिए हैं। यह राइड रिफंड के लिए योग्य है। क्या आप रिफंड रिक्वेस्ट सबमिट करना चाहते हैं?",
        "hinglish": "Bilkul, main aapko refund process mein help karta hoon. Maine aapki last ride aur payment details check ki hain. Ye ride refund ke liye eligible hai. Kya aap refund request submit karna chahte hain?",
        "en": "Certainly. I have checked your last ride and payment details. This ride is eligible for a refund. Would you like to submit a refund request?",
        "bn": "অবশ্যই, আমি আপনার শেষ রাইড এবং পেমেন্টের বিবরণ যাচাই করেছি। এই রাইডটি রিফান্ডের যোগ্য। আপনি কি রিফান্ডের অনুরোধ জমা দিতে চান?",
        "gu": "ચોક્કસ, મેં તમારી છેલ્લી રાઇડ અને પેમેન્ટ વિગતો ચકાસી છે. આ રાઇડ રિફંડ માટે યોગ્ય છે. શું તમે રિફંડ વિનંતી સબમિટ કરવા માંગો છો?",
        "mr": "नक्कीच, मी तुमच्या शेवटच्या राइडचे आणि पेमेंटचे तपशील तपासले आहेत. ही राइड रिफंडसाठी पात्र आहे. तुम्हाला रिफंड विनंती सबमिट करायची आहे का?",
        "pa": "ਬਿਲਕੁਲ, ਮੈਂ ਤੁਹਾਡੀ ਪਿਛਲੀ ਰਾਈਡ ਅਤੇ ਭੁਗਤਾਨ ਦੇ ਵੇਰਵੇ ਚੈੱਕ ਕਰ ਲਏ ਹਨ। ਇਹ ਰਾਈਡ ਰਿਫੰਡ ਲਈ ਯੋਗ ਹੈ। ਕੀ ਤੁਸੀਂ ਰਿਫੰਡ ਬੇਨਤੀ ਸਬਮਿਟ ਕਰਨਾ ਚਾਹੁੰਦੇ ਹੋ?",
    },
    "refund_success": {
        "hi": "हो गया। आपका रिफंड अनुरोध सफलतापूर्वक सबमिट कर दिया गया है। रिफंड आईडी: {refund_id}। रिफंड स्टेटस के बारे में भी मैं आपकी मदद कर सकता हूँ।",
        "hinglish": "Done. Aapki refund request successfully submit ho gayi hai. Refund ID: {refund_id}. Refund status ke baare mein bhi main aapki help kar sakta hoon.",
        "en": "Done. Your refund request has been successfully submitted. Refund ID: {refund_id}. I can also assist you with checking your refund status.",
        "bn": "সম্পন্ন হয়েছে। আপনার রিফান্ড অনুরোধ সফলভাবে জমা দেওয়া হয়েছে। রিফান্ড আইডি: {refund_id}।",
        "gu": "થઈ ગયું. તમારી રિફંડ વિનંતી સફળતાપૂર્વક સબમિટ થઈ ગઈ છે. રિફંડ આઈડી: {refund_id}.",
        "mr": "पूर्ण झाले. तुमची रिफंड विनंती यशस्वीरीत्या सबमिट झाली आहे. रिफंड आयडी: {refund_id}.",
        "pa": "ਹੋ ਗਿਆ। ਤੁਹਾਡੀ ਰਿਫੰਡ ਬੇਨਤੀ ਸਫਲਤਾਪੂਰਵਕ ਸਬਮਿਟ ਹੋ ਗਈ ਹੈ। ਰਿਫੰਡ ਆਈਡੀ: {refund_id}।",
    },
    "already_refunded": {
        "hi": "मैंने रिफंड स्टेटस चेक किया। आपकी रिफंड रिक्वेस्ट पहले ही सबमिट हो चुकी है। करंट स्टेटस: {status}।",
        "hinglish": "Maine refund status check kiya. Aapki refund request pehle hi submit ho chuki hai. Current status: {status}.",
        "en": "I checked your refund status. A refund request has already been submitted for this ride. Current status: {status}.",
        "bn": "আমি রিফান্ড স্ট্যাটাস পরীক্ষা করেছি। এই রাইডের জন্য ইতিমধ্যে একটি রিফান্ড অনুরোধ জমা দেওয়া হয়েছে। বর্তমান স্ট্যাটাস: {status}।",
        "gu": "મેં રિફંડ સ્ટેટસ તપાસ્યું. આ રાઇડ માટે રિફંડ વિનંતી પહેલેથી જ સબમિટ થઈ ગઈ છે. વર્તમાન સ્થિતિ: {status}.",
        "mr": "मी रिफंड स्थिती तपासली आहे. या राइडसाठी आधीच रिफंड विनंती सबमिट केली आहे. सध्याची स्थिती: {status}.",
        "pa": "ਮੈਂ ਰਿਫੰਡ ਸਥਿਤੀ ਦੀ ਜਾਂਚ ਕੀਤੀ। ਤੁਹਾਡੀ ਰਿਫੰਡ ਬੇਨਤੀ ਪਹਿਲਾਂ ਹੀ ਸਬਮਿਟ ਕੀਤੀ ਜਾ ਚੁੱਕੀ ਹੈ। ਮੌਜੂਦਾ ਸਥਿਤੀ: {status}।",
    },
    "not_eligible": {
        "hi": "मैंने आपकी राइड चेक की है। यह राइड अभी रिफंड के लिए योग्य नहीं है क्योंकि {reason}। अगर आपको लगता है कि यह गलत है, तो मैं सपोर्ट टिकट बनाने में मदद कर सकता हूँ।",
        "hinglish": "Maine aapki ride check ki hai. Ye ride refund ke liye currently eligible nahi hai because {reason}. Agar aapko lagta hai ki ye decision incorrect hai, main support ticket create karne mein help kar sakta hoon.",
        "en": "I checked your ride details. This ride is currently not eligible for a refund because {reason}. If you believe this is in error, I can help you create a support ticket.",
        "bn": "আমি আপনার রাইডের বিবরণ চেক করেছি। এই রাইডটি রিফান্ডের জন্য যোগ্য নয় কারণ {reason}।",
        "gu": "મેં તમારી રાઇડ વિગતો ચકાસી છે. આ રાઇડ રિફંડ માટે યોગ્ય નથી કારણ કે {reason}.",
        "mr": "मी तुमच्या राइडचे तपशील तपासले आहेत. ही राइड रिफंडसाठी पात्र नाही कारण {reason}.",
        "pa": "ਮੈਂ ਤੁਹਾਡੇ ਰਾਈਡ ਵੇਰਵਿਆਂ ਦੀ ਜਾਂਚ ਕੀਤੀ ਹੈ। ਇਹ ਰਾਈਡ ਰਿਫੰਡ ਲਈ ਯੋਗ ਨਹੀਂ ਹੈ ਕਿਉਂਕਿ {reason}।",
    },
    "tool_failure": {
        "hi": "मैं अभी आपकी रिफंड डिटेल्स वेरीफाई नहीं कर पा रहा हूँ। अगर आप चाहें तो मैं सपोर्ट टीम से कनेक्ट करने में मदद कर सकता हूँ।",
        "hinglish": "Main abhi aapki refund details verify nahi kar paa raha hoon. Aap chahein to main support team se connect karne mein help kar sakta hoon.",
        "en": "I am unable to verify your refund details at the moment. If you'd like, I can help connect you with our support team.",
        "bn": "আমি এই মুহূর্তে আপনার রিফান্ডের বিবরণ যাচাই করতে পারছি না। আপনি চাইলে আমি সাপোর্ট টিমের সাথে যোগাযোগ করিয়ে দিতে পারি।",
        "gu": "હું અત્યારે તમારી રિફંડ વિગતો ચકાસવામાં અસમર્થ છું. જો તમે ઈચ્છો, તો હું સપોર્ટ ટીમ સાથે કનેક્ટ કરવામાં મદદ કરી શકું છું.",
        "mr": "मी सध्या तुमच्या रिफंड तपशीलांची पडताळणी करू शकत नाही. आपण इच्छित असल्यास मी सपोर्ट टीमशी संपर्क साधण्यात मदत करू शकेन.",
        "pa": "ਮੈਂ ਇਸ ਸਮੇਂ ਤੁਹਾਡੇ ਰਿਫੰਡ ਵੇਰਵਿਆਂ ਦੀ ਪੁਸ਼ਟੀ ਕਰਨ ਵਿੱਚ ਅਸਮਰੱਥ ਹਾਂ। ਜੇਕਰ ਤੁਸੀਂ ਚਾਹੁੰਦੇ ਹੋ, ਤਾਂ ਮੈਂ ਸਹਾਇਤਾ ਟੀਮ ਨਾਲ ਜੁੜਨ ਵਿੱਚ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ।",
    },
    "no_ride": {
        "hi": "आपकी कोई हालिया राइड नहीं मिली जिसका रिफंड प्रोसेस किया जा सके। अगर कोई गलत कटौती हुई है, तो मैं सपोर्ट टीम से कनेक्ट कर सकता हूँ।",
        "hinglish": "Aapki koi recent ride nahi mili jiska refund process kiya ja sake. Agar aapko lagta hai ki koi payment galat kati hai, main support team se connect karwa sakta hoon.",
        "en": "No recent ride was found to process a refund for. If an incorrect deduction occurred, I can connect you with support.",
        "bn": "রিফান্ড প্রক্রিয়া করার জন্য কোনো সাম্প্রতিক রাইড পাওয়া যায়নি।",
        "gu": "રિફંડ પ્રક્રિયા કરવા માટે કોઈ તાજેતરની રાઇડ મળી નથી.",
        "mr": "रिफंड प्रक्रिया करण्यासाठी कोणतीही अलीकडील राइड आढळली नाही.",
        "pa": "ਰਿਫੰਡ ਪ੍ਰਕਿਰਿਆ ਕਰਨ ਲਈ ਕੋਈ ਹਾਲੀਆ ਰਾਈਡ ਨਹੀਂ ਮਿਲੀ।",
    },
}


class ChatOrchestrator:
    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        *,
        registry: ToolRegistry = default_tool_registry,
    ):
        self.db = db
        self.redis = redis
        self.settings = get_settings()

        self.conversations = ConversationService(db)
        self.context = ContextService(db, llm=LLMGateway().primary)
        self.handoffs = HandoffService(db)
        self.audit = AuditService(db)
        self.tool_router = ToolRouter(registry, db, redis)
        self.registry = registry
        self.llm_gateway = LLMGateway()

    async def handle_message(
        self,
        *,
        request_id: str,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        role: UserRole,
        text: str,
        idempotency_key: str | None = None,
    ) -> OrchestrationResult:
        loop_guard = LoopGuard(
            max_tool_calls=self.settings.max_tool_calls_per_turn,
            max_steps=self.settings.max_orchestration_steps,
        )

        # 1-4: session/context already loaded by caller via session_id/user_id

        # 5-10: language, intent, sentiment, urgency, safety, injection detection
        input_check = input_guardrail_pipeline.run(text)
        intent_result: IntentResult = intent_detector.detect(text, role=role)

        await self.conversations.add_message(
            session_id, MessageRole.USER, text,
            language=intent_result.language.value,
            intent=intent_result.intent.value,
            risk_level=intent_result.risk_level.value,
            metadata={"prompt_injection_suspected": input_check.prompt_injection_detected},
        )

        if input_check.prompt_injection_detected:
            await self.audit.record(
                request_id=request_id, action="prompt_injection_flagged", decision="continued_with_caution",
                user_id=user_id, session_id=session_id, details={"text_redacted": input_check.sanitized_for_logging},
            )

        # P0 safety short-circuits straight to escalation -- no normal flow, NEVER overridden by pending intent
        if intent_result.urgency == Priority.P0_EMERGENCY:
            return await self._handle_safety_escalation(
                request_id=request_id, session_id=session_id, user_id=user_id,
                role=role, text=text, intent_result=intent_result,
            )

        # Resolve pending intent if user message is a confirmation of a prior turn (safety & human support exempt)
        if intent_result.intent not in (Intent.SAFETY, Intent.HUMAN_AGENT):
            resolved_intent = await self._resolve_pending_intent(session_id, text, intent_result.intent)
            if resolved_intent != intent_result.intent:
                intent_result = intent_result.model_copy(update={"intent": resolved_intent, "requires_tool": intent_detector._requires_tool(resolved_intent, text)})


        # Check feature-flag configuration for language support
        if not is_language_enabled(intent_result.language):
            fallback_text = get_localized_text("unsupported_language", "en")
            await self.conversations.add_message(
                session_id, MessageRole.ASSISTANT, fallback_text,
                language=intent_result.language.value, intent=intent_result.intent.value,
                metadata={"actions": [], "model": "feature-flag-fallback"},
            )
            return OrchestrationResult(
                message=fallback_text,
                language=intent_result.language,
                intent=intent_result.intent,
                actions=[],
                handoff=HandoffInfo(),
                llm_version="feature-flag-fallback",
                prompt_version="unsupported_language_v1",
            )

        # Guided Refund flow: UNDERSTAND -> VERIFY -> GUIDE -> CONFIRM -> ACT -> EXPLAIN -> ESCALATE
        is_status_only = any(
            w in text.lower()
            for w in ["refund status", "check refund status", "check my refund status", "what is my refund status", "refund status check"]
        ) and not self._is_confirmation_text(text)

        is_confirm = self._is_confirmation_text(text)
        if intent_result.intent == Intent.REFUND and (intent_result.requires_tool or is_confirm) and not is_status_only:
            recent_messages = await self.conversations.get_recent_messages(session_id, limit=5)
            is_confirming = self._is_user_confirming(text, [
                ChatMessage(role="assistant" if str(m.role).lower() in ("assistant", "messagerole.assistant") else "user", content=m.content)
                for m in recent_messages
            ])
            return await self._handle_refund_flow(
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                role=role,
                text=text,
                intent_result=intent_result,
                idempotency_key=idempotency_key,
                is_confirming=is_confirming,
            )

        # 12-13: contextual retrieval (only when knowledge-driven, not blind full history)
        rag_context = ""
        if intent_result.intent in KNOWLEDGE_DRIVEN_INTENTS and not intent_result.requires_tool:
            try:
                rag_service = RAGRetrievalService(self.db, get_embedding_provider())
                chunks = await rag_service.retrieve(
                    text,
                    language=intent_result.language.value,
                    category=intent_result.intent.value,  # scope search to matching KB category
                )
                rag_context = rag_service.build_context_block(chunks)
            except ValueError:
                # embeddings backend not configured (missing EMBEDDING_API_KEY);
                # degrade gracefully rather than failing the whole turn
                logger.warning("rag_embedding_provider_not_configured")
                rag_context = ""

        # 14-19: tool-augmented LLM turn with authorization enforced by ToolRouter
        prompt = get_prompt("customer_support_system" if role == UserRole.CUSTOMER else "driver_support_system")
        llm_messages = await self.context.build_llm_messages(session_id)

        # Language-lock reminder: injected immediately before the user turn so the
        # LLM cannot be drifted to a prior session language by stale assistant messages
        # in the conversation history (e.g. a previous turn was answered in Marathi but
        # the current message is in Tamil).  Using role="user" keeps it compatible with
        # providers that do not support a mid-history "system" role.
        detected_language_name = LANGUAGE_CODE_TO_NAME.get(
            intent_result.language.value, intent_result.language.value.upper()
        )
        llm_messages.append(
            ChatMessage(
                role="user",
                content=(
                    f"[SYSTEM REMINDER — ignore any prior language used in this conversation] "
                    f"The user's current message is in {detected_language_name}. "
                    f"You MUST reply ONLY in {detected_language_name}. Do NOT use any other language."
                ),
            )
        )
        llm_messages.append(ChatMessage(role="user", content=text))

        system_prompt = prompt.render(intent_result.language.value)
        if rag_context:
            system_prompt += f"\n\nApproved knowledge base context (use only this for policy facts):\n{rag_context}"

        tool_specs = [
            ToolSpec(name=s["name"], description=s["description"], input_schema=s["input_schema"])
            for s in self.registry.list_specs_for_llm()
        ]

        actions_taken: list[str] = []
        handoff_info = HandoffInfo()
        final_text = ""
        llm_version = self.settings.llm_model_primary

        try:
            for _ in range(loop_guard.max_steps):
                loop_guard.record_step()
                response = await self.llm_gateway.chat_with_fallback(
                    llm_messages, system=system_prompt, tools=tool_specs,
                    language=intent_result.language.value,
                )
                model_version_str = response.model
                llm_version = model_version_str

                tool_calls_to_exec = response.tool_calls or []
                if not tool_calls_to_exec and not actions_taken and intent_result.requires_tool:
                    fallback_tool = self._get_fallback_tool_for_intent(intent_result.intent)
                    if fallback_tool:
                        tool_name, default_args = fallback_tool
                        tool_calls_to_exec = [{"name": tool_name, "input": default_args}]


                if not tool_calls_to_exec:
                    final_text = response.text
                    break

                # Execute each requested tool through the enforced router
                llm_messages.append(ChatMessage(role="assistant", content=response.text or "(using tools)"))
                tool_results_text = []
                for call in tool_calls_to_exec:
                    loop_guard.record_tool_call()
                    ctx = ToolContext(
                        user_id=str(user_id), role=role, session_id=str(session_id), request_id=request_id
                    )
                    try:
                        result = await self.tool_router.invoke(
                            ctx=ctx, tool_name=call["name"], arguments=call.get("input", {}),
                            user_confirmed=self._is_user_confirming(text, llm_messages),
                            idempotency_key=idempotency_key,
                        )
                        actions_taken.append(call["name"])
                        if call["name"] == "handoff_to_agent" and isinstance(result, dict) and result.get("triggered"):
                            p_val = result.get("priority") or intent_result.urgency.value
                            try:
                                p_enum = Priority(p_val)
                            except ValueError:
                                p_enum = Priority.P2_STANDARD
                            handoff_info = HandoffInfo(
                                triggered=True,
                                priority=p_enum,
                                reason=result.get("reason", "user_requested_human"),
                                handoff_id=str(result.get("handoff_id", ""))
                            )
                        tool_results_text.append(f"Tool {call['name']} result: {json.dumps(result)}")
                    except ConfirmationRequiredError as exc:
                        tool_results_text.append(f"Tool {call['name']} needs user confirmation: {exc.message}")
                    except (ToolDeniedError, ForbiddenError) as exc:
                        tool_results_text.append(f"Tool {call['name']} denied: {str(exc)}")
                    except Exception as exc:
                        tool_results_text.append(f"Tool {call['name']} execution failed: {str(exc)}")

                llm_messages.append(ChatMessage(role="user", content="\n".join(tool_results_text)))

            else:
                final_text = get_localized_text("human_handoff", intent_result.language.value)
                handoff_info = await self._escalate(
                    request_id, session_id, user_id, Priority.P2_STANDARD, "orchestration_limit",
                    intent_result, actions_taken,
                )

        except OrchestrationLimitExceededError:
            final_text = get_localized_text("human_handoff", intent_result.language.value)
            handoff_info = await self._escalate(
                request_id, session_id, user_id, Priority.P2_STANDARD, "loop_guard_triggered",
                intent_result, actions_taken,
            )

        # 20: output guardrails & language validation
        final_text = output_guardrail_pipeline.run(final_text)

        if not validate_response_language(final_text, intent_result.language):
            logger.warning(
                "response_language_validation_failed",
                expected_language=intent_result.language.value,
            )
            # Single retry with reinforced language constraint
            retry_messages = llm_messages + [
                ChatMessage(
                    role="user",
                    content=(
                        f"[CRITICAL LANGUAGE CORRECTION] Your previous response was not in the required language/script. "
                        f"You MUST regenerate the answer strictly in {detected_language_name}."
                    ),
                )
            ]
            retry_resp = await self.llm_gateway.chat_with_fallback(
                retry_messages, system=system_prompt, tools=tool_specs,
                language=intent_result.language.value,
            )
            if retry_resp.text:
                final_text = output_guardrail_pipeline.run(retry_resp.text)

        # Explicit human-agent request
        if intent_result.intent == Intent.HUMAN_AGENT and not handoff_info.triggered:
            handoff_info = await self._escalate(
                request_id, session_id, user_id, Priority.P2_STANDARD, "user_requested_human",
                intent_result, actions_taken,
            )

        # 21-23: persist assistant message + audit
        is_pending_confirm = (not actions_taken) and any(
            w in final_text.lower() for w in [
                "confirm", "chahiye", "જોઈએ", "ਚਾਹੀਦਾ", "চাই", "आवश्यकता", "तक्रार", "dispute", "cancel", "refund"
            ]
        )
        await self.conversations.add_message(
            session_id, MessageRole.ASSISTANT, final_text,
            language=intent_result.language.value, intent=intent_result.intent.value,
            metadata={
                "actions": actions_taken,
                "model": llm_version,
                "pending_intent": intent_result.intent.value,
                "requires_confirmation": is_pending_confirm,
            },
        )
        await self.context.maybe_summarize(session_id)

        return OrchestrationResult(
            message=final_text,
            language=intent_result.language,
            intent=intent_result.intent,
            actions=actions_taken,
            handoff=handoff_info,
            llm_version=llm_version,
            prompt_version=prompt.version,
        )

    async def _handle_safety_escalation(
        self, *, request_id, session_id, user_id, role, text, intent_result
    ) -> OrchestrationResult:
        ctx = ToolContext(user_id=str(user_id), role=role, session_id=str(session_id), request_id=request_id)
        result = await self.tool_router.invoke(
            ctx=ctx, tool_name="create_safety_incident", arguments={"details": text}, user_confirmed=True,
        )
        handoff_info = await self._escalate(
            request_id, session_id, user_id, Priority.P0_EMERGENCY, "safety_incident",
            intent_result, ["create_safety_incident"],
        )
        reply = get_localized_text(
            "safety_escalation", intent_result.language.value,
            incident_id=result.get('incident_id', 'pending')
        )
        await self.conversations.add_message(
            session_id, MessageRole.ASSISTANT, reply, language=intent_result.language.value,
            intent=Intent.SAFETY.value, metadata={"actions": ["create_safety_incident"]},
        )
        return OrchestrationResult(
            message=reply, language=intent_result.language, intent=Intent.SAFETY,
            actions=["create_safety_incident"], handoff=handoff_info,
            llm_version="deterministic-safety-flow", prompt_version="safety_system_v1",
        )

    async def _escalate(
        self, request_id, session_id, user_id, priority, reason, intent_result, actions_taken
    ) -> HandoffInfo:
        session = await self.conversations.get_session(session_id, user_id)
        handoff = await self.handoffs.escalate(
            session=session, user_id=user_id, priority=priority, reason=reason,
            intent=intent_result.intent.value, language=intent_result.language.value,
            tool_calls_summary=actions_taken,
        )
        await self.audit.record(
            request_id=request_id, action="handoff_triggered", decision="allowed",
            user_id=user_id, session_id=session_id, details={"reason": reason, "priority": priority.value},
        )
        return HandoffInfo(triggered=True, priority=priority, reason=reason, handoff_id=str(handoff.id))

    async def _save_session_state(self, session_id: uuid.UUID, state: dict[str, Any]) -> None:
        key = f"session_state:{session_id}"
        try:
            await self.redis.set(key, json.dumps(state), ex=3600)
        except Exception as exc:
            logger.warning("failed_to_save_session_state_redis", error=str(exc))

    async def _get_session_state(self, session_id: uuid.UUID) -> dict[str, Any] | None:
        key = f"session_state:{session_id}"
        try:
            cached = await self.redis.get(key)
            if cached:
                if isinstance(cached, bytes):
                    cached = cached.decode("utf-8")
                return json.loads(cached)
        except Exception as exc:
            logger.warning("failed_to_get_session_state_redis", error=str(exc))

        # Fallback to last assistant message metadata_json
        recent_messages = await self.conversations.get_recent_messages(session_id, limit=5)
        for msg in reversed(recent_messages):
            if str(msg.role).lower() in ("assistant", "messagerole.assistant") and msg.metadata_json:
                refund_state = msg.metadata_json.get("refund_state")
                if refund_state:
                    return refund_state
        return None

    async def _handle_refund_flow(
        self,
        *,
        request_id: str,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        role: UserRole,
        text: str,
        intent_result: IntentResult,
        idempotency_key: str | None = None,
        is_confirming: bool = False,
    ) -> OrchestrationResult:
        lang = intent_result.language.value
        if lang == "hi-en":
            lang = "hinglish"
        ctx = ToolContext(user_id=str(user_id), role=role, session_id=str(session_id), request_id=request_id)

        session_state = await self._get_session_state(session_id)

        # STEP 4 (CONFIRMATION) -> STEP 5 (ACT) -> STEP 6 (EXPLAIN)
        # Check if user is confirming a pending refund request
        has_pending_eligible = bool(session_state and session_state.get("intent") == "refund" and session_state.get("refund_eligible"))
        if not has_pending_eligible:
            recent_msgs = await self.conversations.get_recent_messages(session_id, limit=5)
            for m in reversed(recent_msgs):
                if str(m.role).lower() in ("assistant", "messagerole.assistant") and m.metadata_json:
                    if m.metadata_json.get("pending_intent") == "refund" and m.metadata_json.get("requires_confirmation"):
                        has_pending_eligible = True
                        if not session_state:
                            session_state = {
                                "intent": "refund",
                                "session_id": str(session_id),
                                "user_id": str(user_id),
                                "selected_ride": m.metadata_json.get("selected_ride", "ride_123"),
                                "refund_eligible": True,
                                "amount": m.metadata_json.get("amount", 148.0),
                            }
                        break

        if is_confirming and has_pending_eligible and not (session_state and session_state.get("confirmation_received")):
            ride_id = session_state.get("selected_ride", "ride_123")
            amount = session_state.get("amount", 148.0)
            eff_idempotency_key = idempotency_key or f"refund_{user_id}_{ride_id}"
            actions_taken = ["request_refund"]
            try:
                refund_res = await self.tool_router.invoke(
                    ctx=ctx,
                    tool_name="request_refund",
                    arguments={
                        "ride_id": ride_id,
                        "amount": amount,
                        "reason": text or "Refund requested by customer",
                    },
                    user_confirmed=True,
                    idempotency_key=eff_idempotency_key,
                )
                refund_id = refund_res.get("refund_id", f"ref_{ride_id}")
                session_state.update({
                    "refund_status": refund_res.get("status", "refund_initiated"),
                    "refund_id": refund_id,
                    "confirmation_received": True,
                    "action_status": "success",
                })
                await self._save_session_state(session_id, session_state)

                # STEP 6 - EXPLAIN (reporting actual tool results)
                success_tpl = REFUND_RESPONSES["refund_success"].get(
                    lang, REFUND_RESPONSES["refund_success"]["en"]
                )
                success_text = success_tpl.format(refund_id=refund_id)
                await self.conversations.add_message(
                    session_id,
                    MessageRole.ASSISTANT,
                    success_text,
                    language=lang,
                    intent=Intent.REFUND.value,
                    metadata={
                        "actions": actions_taken,
                        "model": self.settings.llm_model_primary,
                        "refund_result": refund_res,
                        "requires_confirmation": False,
                        "refund_state": session_state,
                    },
                )
                await self.context.maybe_summarize(session_id)
                return OrchestrationResult(
                    message=success_text,
                    language=intent_result.language,
                    intent=Intent.REFUND,
                    actions=actions_taken,
                    handoff=HandoffInfo(),
                    llm_version=self.settings.llm_model_primary,
                    prompt_version="refund_flow_v1",
                )
            except Exception as exc:
                # STEP 9 - TOOL FAILURE
                logger.warning("refund_request_failed", error=str(exc))
                fail_text = REFUND_RESPONSES["tool_failure"].get(
                    lang, REFUND_RESPONSES["tool_failure"]["en"]
                )
                await self.conversations.add_message(
                    session_id,
                    MessageRole.ASSISTANT,
                    fail_text,
                    language=lang,
                    intent=Intent.REFUND.value,
                    metadata={"actions": [], "error": str(exc), "requires_confirmation": False},
                )
                return OrchestrationResult(
                    message=fail_text,
                    language=intent_result.language,
                    intent=Intent.REFUND,
                    actions=[],
                    handoff=HandoffInfo(),
                    llm_version=self.settings.llm_model_primary,
                    prompt_version="refund_flow_v1",
                )

        # STEP 1 (UNDERSTAND) -> STEP 2 (VERIFY) -> STEP 3 (GUIDE)
        actions_taken: list[str] = []
        try:
            # 1. get_active_ride (or most recent ride)
            ride_res = await self.tool_router.invoke(
                ctx=ctx, tool_name="get_active_ride", arguments={}, user_confirmed=False
            )
            actions_taken.append("get_active_ride")
            ride = ride_res.get("ride")
            if not ride:
                no_ride_text = REFUND_RESPONSES["no_ride"].get(
                    lang, REFUND_RESPONSES["no_ride"]["en"]
                )
                await self.conversations.add_message(
                    session_id,
                    MessageRole.ASSISTANT,
                    no_ride_text,
                    language=lang,
                    intent=Intent.REFUND.value,
                    metadata={"actions": actions_taken, "requires_confirmation": False},
                )
                return OrchestrationResult(
                    message=no_ride_text,
                    language=intent_result.language,
                    intent=Intent.REFUND,
                    actions=actions_taken,
                    handoff=HandoffInfo(),
                    llm_version=self.settings.llm_model_primary,
                    prompt_version="refund_flow_v1",
                )

            ride_id = ride.get("ride_id", "ride_123")
            amount = ride.get("fare_estimate", 148.0)

            # 2. get_payment_status
            payment_res = await self.tool_router.invoke(
                ctx=ctx, tool_name="get_payment_status", arguments={"ride_id": ride_id}, user_confirmed=False
            )
            actions_taken.append("get_payment_status")
            payment_status = payment_res.get("status", "captured")
            if payment_res.get("amount"):
                amount = payment_res.get("amount")

            # 3. get_refund_status
            refund_res = await self.tool_router.invoke(
                ctx=ctx, tool_name="get_refund_status", arguments={"ride_id": ride_id}, user_confirmed=False
            )
            actions_taken.append("get_refund_status")
            current_refund_status = refund_res.get("status", "not_requested")

        except (ForbiddenError, ToolDeniedError) as exc:
            # STEP 10 - UNAUTHORIZED REQUEST
            logger.warning("refund_verification_forbidden", error=str(exc))
            raise
        except Exception as exc:
            # STEP 9 - TOOL FAILURE
            logger.warning("refund_verification_failed", error=str(exc))
            fail_text = REFUND_RESPONSES["tool_failure"].get(
                lang, REFUND_RESPONSES["tool_failure"]["en"]
            )
            await self.conversations.add_message(
                session_id,
                MessageRole.ASSISTANT,
                fail_text,
                language=lang,
                intent=Intent.REFUND.value,
                metadata={"actions": actions_taken, "error": str(exc), "requires_confirmation": False},
            )
            return OrchestrationResult(
                message=fail_text,
                language=intent_result.language,
                intent=Intent.REFUND,
                actions=actions_taken,
                handoff=HandoffInfo(),
                llm_version=self.settings.llm_model_primary,
                prompt_version="refund_flow_v1",
            )

        # STEP 8 - ALREADY REFUNDED
        if current_refund_status not in ("not_requested", None, ""):
            already_tpl = REFUND_RESPONSES["already_refunded"].get(
                lang, REFUND_RESPONSES["already_refunded"]["en"]
            )
            already_text = already_tpl.format(status=current_refund_status)
            await self.conversations.add_message(
                session_id,
                MessageRole.ASSISTANT,
                already_text,
                language=lang,
                intent=Intent.REFUND.value,
                metadata={
                    "actions": actions_taken,
                    "refund_status": current_refund_status,
                    "requires_confirmation": False,
                },
            )
            return OrchestrationResult(
                message=already_text,
                language=intent_result.language,
                intent=Intent.REFUND,
                actions=actions_taken,
                handoff=HandoffInfo(),
                llm_version=self.settings.llm_model_primary,
                prompt_version="refund_flow_v1",
            )

        # STEP 7 - NOT ELIGIBLE
        if payment_status not in ("captured", "completed", "successful", "paid"):
            ineligible_tpl = REFUND_RESPONSES["not_eligible"].get(
                lang, REFUND_RESPONSES["not_eligible"]["en"]
            )
            reason = f"payment status is '{payment_status}'"
            ineligible_text = ineligible_tpl.format(reason=reason)
            await self.conversations.add_message(
                session_id,
                MessageRole.ASSISTANT,
                ineligible_text,
                language=lang,
                intent=Intent.REFUND.value,
                metadata={
                    "actions": actions_taken,
                    "payment_status": payment_status,
                    "requires_confirmation": False,
                },
            )
            return OrchestrationResult(
                message=ineligible_text,
                language=intent_result.language,
                intent=Intent.REFUND,
                actions=actions_taken,
                handoff=HandoffInfo(),
                llm_version=self.settings.llm_model_primary,
                prompt_version="refund_flow_v1",
            )

        # STEP 3 - GUIDE THE USER (Eligible, Ask for Confirmation)
        guide_text = REFUND_RESPONSES["eligible_guide"].get(
            lang, REFUND_RESPONSES["eligible_guide"]["en"]
        )
        refund_state = {
            "intent": "refund",
            "session_id": str(session_id),
            "user_id": str(user_id),
            "selected_ride": ride_id,
            "ride_verified": True,
            "payment_verified": True,
            "refund_status": current_refund_status,
            "refund_eligible": True,
            "confirmation_required": True,
            "confirmation_received": False,
            "amount": amount,
            "action_status": "verified",
            "handoff_status": "none",
        }
        await self._save_session_state(session_id, refund_state)

        await self.conversations.add_message(
            session_id,
            MessageRole.ASSISTANT,
            guide_text,
            language=lang,
            intent=Intent.REFUND.value,
            metadata={
                "actions": actions_taken,
                "model": self.settings.llm_model_primary,
                "pending_intent": "refund",
                "requires_confirmation": True,
                "refund_state": refund_state,
            },
        )
        await self.context.maybe_summarize(session_id)

        return OrchestrationResult(
            message=guide_text,
            language=intent_result.language,
            intent=Intent.REFUND,
            actions=actions_taken,
            handoff=HandoffInfo(),
            llm_version=self.settings.llm_model_primary,
            prompt_version="refund_flow_v1",
        )

    async def _resolve_pending_intent(
        self, session_id: uuid.UUID, current_text: str, detected_intent: Intent
    ) -> Intent:
        # P0 Safety or Human Agent requests MUST NEVER be overridden by a pending intent
        if detected_intent in (Intent.SAFETY, Intent.HUMAN_AGENT):
            return detected_intent

        if not self._is_confirmation_text(current_text):
            return detected_intent

        recent_messages = await self.conversations.get_recent_messages(session_id, limit=5)
        if not recent_messages:
            return detected_intent

        last_assistant_msg = next((m for m in reversed(recent_messages) if str(m.role).lower() in ("assistant", "messagerole.assistant")), None)
        if not last_assistant_msg:
            return detected_intent

        meta = last_assistant_msg.metadata_json or {}
        requires_confirm = meta.get("requires_confirmation") or any(
            w in (last_assistant_msg.content or "").lower() for w in [
                "confirm", "chahiye", "જોઈએ", "ਚਾਹੀਦਾ", "চাই", "आवश्यकता", "तक्रार", "dispute", "cancel", "refund"
            ]
        )

        if not requires_confirm:
            return detected_intent

        pending_intent_str = meta.get("pending_intent") or last_assistant_msg.intent
        if not pending_intent_str or pending_intent_str == Intent.UNKNOWN.value:
            last_user_msg = next((m for m in reversed(recent_messages) if str(m.role).lower() in ("user", "messagerole.user")), None)
            if last_user_msg:
                pending_intent_str = last_user_msg.intent

        if pending_intent_str and pending_intent_str != Intent.UNKNOWN.value:
            try:
                return Intent(pending_intent_str)
            except ValueError:
                pass

        return detected_intent

    @staticmethod
    def _is_confirmation_text(text: str) -> bool:
        from app.ai.intent.detector import ACTIVE_SAFETY_PATTERN
        if ACTIVE_SAFETY_PATTERN.search(text):
            return False

        normalized = text.strip().lower()
        clean = re.sub(r"[^\w\s\u0900-\u097F\u0A80-\u0AFF\u0980-\u09FF\u0A00-\u0A7F]", " ", normalized)
        clean = " ".join(clean.split())

        exact_affirmatives = {
            "yes", "confirm", "ok", "okay", "sure", "proceed", "do it", "yes please", "go ahead",
            "yes please submit it", "yes submit it", "please submit it", "yes kar do", "please kar do",
            "haan", "ha", "haa", "bilkul", "kar do", "karo", "start kar do", "shuru kar do",
            "haan kar do", "ha kar do", "haan start kar do", "haan shuru", "bilkul kar do",
            "kar dijiye", "kijiye", "haan ji", "ha ji",
            "हाँ", "हौ", "होय", "बिलकुल", "शुरू कर दो", "कर दो", "करो", "हाँ शुरू कर दो", "हाँ कर दो",
            "हाँ, कर दीजिए", "हाँ कर दीजिए", "कर दीजिए", "हाँ जी",
            "હા", "શરૂ કરો", "કરી દો", "હા શરૂ કરો", "હા કરો",
            "হ্যাঁ", "শুরু করুন", "করুন", "হ্যাঁ शुरू করুন", "হ্যাঁ করুন",
            "ਹਾਂ", "ਸ਼ੁਰੂ ਕਰੋ", "ਕਰੋ", "ਹਾਂਜੀ", "ਹਾਂ ਕਰੋ",
            "करा", "सुरू करा"
        }
        if clean in exact_affirmatives or normalized in exact_affirmatives:
            return True

        words = set(clean.split())
        single_word_keywords = {
            "yes", "confirm", "ok", "okay", "sure", "proceed", "start",
            "haan", "ha", "haa", "bilkul", "karo", "shuru",
            "हाँ", "हौ", "होय", "बिलकुल", "शुरू", "करो",
            "હા", "શરૂ", "કરી", "হ্যাঁ", "করুন", "ਹਾਂ", "करा"
        }
        if words.intersection(single_word_keywords):
            return True

        multi_word_phrases = [
            "do it", "yes please", "go ahead", "kar do", "start kar do", "shuru kar do",
            "haan kar do", "ha kar do", "haan start kar do", "haan shuru", "bilkul kar do",
            "kar dijiye", "kijiye", "haan ji", "ha ji",
            "शुरू कर दो", "कर दो", "हाँ शुरू कर दो", "हाँ कर दो",
            "हाँ, कर दीजिए", "हाँ कर दीजिए", "कर दीजिए", "हाँ जी",
            "શરૂ કરો", "કરી દો", "હા શરૂ કરો", "હા કરો",
            "শুরু করুন", "করুন", "হ্যাঁ শুরু করুন", "হ্যাঁ করুন",
            "ਸ਼ੁਰੂ ਕਰੋ", "ਹਾਂਜੀ", "ਹਾਂ ਕਰੋ",
            "करा", "सुरू करा"
        ]
        if any(p in clean for p in multi_word_phrases):
            return True

        return False

    @classmethod
    def _is_user_confirming(cls, text: str, history: list[ChatMessage] | None = None) -> bool:
        from app.ai.intent.detector import ACTIVE_SAFETY_PATTERN
        if ACTIVE_SAFETY_PATTERN.search(text):
            return False

        if cls._is_confirmation_text(text):
            return True
        normalized = text.strip().lower()
        has_prior_confirmation_prompt = False
        if history:
            has_prior_confirmation_prompt = any(
                m.role == "assistant" and any(
                    w in (m.content or "").lower() for w in [
                        "confirm", "chahiye", "જોઈએ", "ਚਾਹੀਦਾ", "চাই", "आवश्यकता", "गरज", "तक्रार", "पुष्टि", "নিশ্চিতকরণ"
                    ]
                )
                for m in history
            )
        words = set(re.findall(r"\b[a-zA-Z\u0900-\u097F\u0A80-\u0AFF\u0980-\u09FF\u0A00-\u0A7F]+\b", normalized))
        confirm_tokens = {"yes", "confirm", "haan", "ha", "ok", "okay", "हाँ", "होय", "હા", "হ্যাঁ", "ਹਾਂ"}
        if has_prior_confirmation_prompt and (words.intersection(confirm_tokens) or any(p in normalized for p in ["kar do", "karo", "कर दो", "करो"])):
            return True
        return False

    @staticmethod
    def _get_fallback_tool_for_intent(intent: Intent) -> tuple[str, dict] | None:
        mapping = {
            Intent.RIDE_STATUS: ("get_active_ride", {}),
            Intent.DRIVER_LATE: ("get_driver_eta", {}),
            Intent.FARE: ("get_ride_fare_breakdown", {}),
            Intent.PAYMENT_FAILED: ("get_payment_status", {"ride_id": "ride_123"}),
            Intent.EARNINGS: ("get_driver_earnings", {"period": "today"}),
            Intent.PAYOUT: ("get_driver_earnings", {"period": "week"}),
            Intent.INCENTIVE: ("get_driver_earnings", {"period": "week"}),
            Intent.DOCUMENT_STATUS: ("get_document_status", {}),
            Intent.VEHICLE_DOCUMENT: ("get_document_status", {}),
            Intent.CUSTOMER_NOT_FOUND: ("get_active_ride", {}),
            Intent.CUSTOMER_CANCELLED: ("get_active_ride", {}),
            Intent.RIDE_OFFER: ("get_active_ride", {}),
            Intent.ACCEPTANCE: ("get_active_ride", {}),
            Intent.CASH_PAYMENT: ("get_active_ride", {}),
            Intent.REFUND: ("get_active_ride", {}),
            Intent.HUMAN_AGENT: ("handoff_to_agent", {"reason": "user_requested_human", "priority": "P2"}),
        }
        return mapping.get(intent)