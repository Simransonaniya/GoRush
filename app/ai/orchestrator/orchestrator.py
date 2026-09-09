import json
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
        intent_result: IntentResult = intent_detector.detect(text)

        # Resolve pending intent if user message is a confirmation of a prior turn
        resolved_intent = await self._resolve_pending_intent(session_id, text, intent_result.intent)
        if resolved_intent != intent_result.intent:
            intent_result = intent_result.model_copy(update={"intent": resolved_intent})

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

        # P0 safety short-circuits straight to escalation -- no normal flow
        if intent_result.urgency == Priority.P0_EMERGENCY:
            return await self._handle_safety_escalation(
                request_id=request_id, session_id=session_id, user_id=user_id,
                role=role, text=text, intent_result=intent_result,
            )


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

        # 12-13: contextual retrieval (only when knowledge-driven, not blind full history)
        rag_context = ""
        if intent_result.intent in KNOWLEDGE_DRIVEN_INTENTS:
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

    async def _resolve_pending_intent(
        self, session_id: uuid.UUID, current_text: str, detected_intent: Intent
    ) -> Intent:
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
        import re
        normalized = text.strip().lower()
        clean = re.sub(r"[^\w\s\u0900-\u097F\u0A80-\u0AFF\u0980-\u09FF\u0A00-\u0A7F]", " ", normalized)
        clean = " ".join(clean.split())

        exact_affirmatives = {
            "yes", "confirm", "ok", "okay", "sure", "proceed", "do it", "yes please", "go ahead",
            "haan", "ha", "haa", "bilkul", "kar do", "karo", "start kar do", "shuru kar do",
            "haan kar do", "haan start kar do", "haan shuru", "bilkul kar do",
            "हाँ", "हौ", "होय", "बिलकुल", "शुरू कर दो", "कर दो", "करो", "हाँ शुरू कर दो", "हाँ कर दो",
            "હા", "શરૂ કરો", "કરી દો", "હા શરૂ કરો", "હા કરો",
            "হ্যাঁ", "শুরু করুন", "করুন", "হ্যাঁ শুরু করুন", "হ্যাঁ করুন",
            "ਹਾਂ", "ਸ਼ੁਰੂ ਕਰੋ", "ਕਰੋ", "ਹਾਂਜੀ", "ਹਾਂ ਕਰੋ",
            "करा", "सुरू करा"
        }
        if clean in exact_affirmatives or normalized in exact_affirmatives:
            return True

        keywords = [
            "yes", "confirm", "ok", "okay", "sure", "proceed", "do it", "yes please", "go ahead",
            "haan", "ha", "bilkul", "kar do", "karo", "shuru", "start",
            "हाँ", "हौ", "होय", "बिलकुल", "शुरू", "कर दो", "करो",
            "હા", "શરૂ", "કરી", "হ্যাঁ", "করুন", "ਹਾਂ", "करा"
        ]
        if any(w in clean for w in keywords):
            return True

        return False

    @classmethod
    def _is_user_confirming(cls, text: str, history: list[ChatMessage] | None = None) -> bool:
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
        if has_prior_confirmation_prompt and any(w in normalized for w in ["yes", "confirm", "haan", "ha", "ok", "kar do", "karo"]):
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
            Intent.DOCUMENT_STATUS: ("get_document_status", {}),
        }
        return mapping.get(intent)