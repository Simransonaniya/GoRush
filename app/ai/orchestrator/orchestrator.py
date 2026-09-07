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
from app.ai.prompts.registry import get_prompt
from app.audit.service import AuditService
from app.common.enums.chat import Intent, MessageRole, Priority, UserRole
from app.common.exceptions.base import ConfirmationRequiredError, ToolDeniedError
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
KNOWLEDGE_DRIVEN_INTENTS = {
    Intent.FAQ, Intent.CANCELLATION, Intent.REFUND, Intent.PROMO,
    Intent.PRIVACY, Intent.ACCOUNT, Intent.WALLET,
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
    ) -> OrchestrationResult:
        loop_guard = LoopGuard(
            max_tool_calls=self.settings.max_tool_calls_per_turn,
            max_steps=self.settings.max_orchestration_steps,
        )

        # 1-4: session/context already loaded by caller via session_id/user_id

        # 5-10: language, intent, sentiment, urgency, safety, injection detection
        input_check = input_guardrail_pipeline.run(text)
        intent_result: IntentResult = intent_detector.detect(text)

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
        if intent_result.intent == Intent.SAFETY or intent_result.urgency == Priority.P0_EMERGENCY:
            return await self._handle_safety_escalation(
                request_id=request_id, session_id=session_id, user_id=user_id,
                role=role, text=text, intent_result=intent_result,
            )

        # 12-13: contextual retrieval (only when knowledge-driven, not blind full history)
        rag_context = ""
        if intent_result.intent in KNOWLEDGE_DRIVEN_INTENTS:
            try:
                rag_service = RAGRetrievalService(self.db, get_embedding_provider())
                chunks = await rag_service.retrieve(text, language=intent_result.language.value)
                rag_context = rag_service.build_context_block(chunks)
            except ValueError:
                # embeddings backend not configured (missing EMBEDDING_API_KEY);
                # degrade gracefully rather than failing the whole turn
                logger.warning("rag_embedding_provider_not_configured")
                rag_context = ""

        # 14-19: tool-augmented LLM turn with authorization enforced by ToolRouter
        prompt = get_prompt("customer_support_system" if role == UserRole.CUSTOMER else "driver_support_system")
        llm_messages = await self.context.build_llm_messages(session_id)
        llm_messages.append(ChatMessage(role="user", content=text))

        system_prompt = prompt.content
        if rag_context:
            system_prompt += f"\n\nApproved knowledge base context (use only this for policy facts):\n{rag_context}"

        tool_specs = [
            ToolSpec(name=s["name"], description=s["description"], input_schema=s["input_schema"])
            for s in self.registry.list_specs_for_llm()
        ]

        actions_taken: list[str] = []
        handoff_info = HandoffInfo()
        final_text = ""
        model_version = self.settings.llm_model_primary

        try:
            for _ in range(loop_guard.max_steps):
                loop_guard.record_step()
                response = await self.llm_gateway.chat_with_fallback(
                    llm_messages, system=system_prompt, tools=tool_specs
                )
                model_version = response.model

                if not response.tool_calls:
                    final_text = response.text
                    break

                # Execute each requested tool through the enforced router
                llm_messages.append(ChatMessage(role="assistant", content=response.text or "(using tools)"))
                tool_results_text = []
                for call in response.tool_calls:
                    loop_guard.record_tool_call()
                    ctx = ToolContext(
                        user_id=str(user_id), role=role, session_id=str(session_id), request_id=request_id
                    )
                    try:
                        result = await self.tool_router.invoke(
                            ctx=ctx, tool_name=call["name"], arguments=call.get("input", {}),
                            user_confirmed=self._looks_like_confirmation(text),
                        )
                        actions_taken.append(call["name"])
                        tool_results_text.append(f"Tool {call['name']} result: {json.dumps(result)}")
                    except ConfirmationRequiredError as exc:
                        tool_results_text.append(f"Tool {call['name']} needs user confirmation: {exc.message}")
                    except ToolDeniedError as exc:
                        tool_results_text.append(f"Tool {call['name']} denied: {exc.message}")

                llm_messages.append(ChatMessage(role="user", content="\n".join(tool_results_text)))

            else:
                final_text = "Let me connect you with a support agent to make sure this is handled correctly."
                handoff_info = await self._escalate(
                    request_id, session_id, user_id, Priority.P2_STANDARD, "orchestration_limit",
                    intent_result, actions_taken,
                )

        except OrchestrationLimitExceededError:
            final_text = "Let me connect you with a support agent to make sure this is handled correctly."
            handoff_info = await self._escalate(
                request_id, session_id, user_id, Priority.P2_STANDARD, "loop_guard_triggered",
                intent_result, actions_taken,
            )

        # 20: output guardrails
        final_text = output_guardrail_pipeline.run(final_text)

        # Explicit human-agent request
        if intent_result.intent == Intent.HUMAN_AGENT and not handoff_info.triggered:
            handoff_info = await self._escalate(
                request_id, session_id, user_id, Priority.P2_STANDARD, "user_requested_human",
                intent_result, actions_taken,
            )

        # 21-23: persist assistant message + audit
        await self.conversations.add_message(
            session_id, MessageRole.ASSISTANT, final_text,
            language=intent_result.language.value, intent=intent_result.intent.value,
            metadata={"actions": actions_taken, "model": model_version},
        )
        await self.context.maybe_summarize(session_id)

        return OrchestrationResult(
            message=final_text,
            language=intent_result.language,
            intent=intent_result.intent,
            actions=actions_taken,
            handoff=handoff_info,
            model_version=model_version,
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
        reply = (
            "I've alerted our safety team immediately and they're being connected to you now. "
            f"Reference: {result.get('incident_id', 'pending')}. Please stay safe."
        )
        await self.conversations.add_message(
            session_id, MessageRole.ASSISTANT, reply, language=intent_result.language.value,
            intent=Intent.SAFETY.value, metadata={"actions": ["create_safety_incident"]},
        )
        return OrchestrationResult(
            message=reply, language=intent_result.language, intent=Intent.SAFETY,
            actions=["create_safety_incident"], handoff=handoff_info,
            model_version="deterministic-safety-flow", prompt_version="safety_system_v1",
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

    @staticmethod
    def _looks_like_confirmation(text: str) -> bool:
        normalized = text.strip().lower()
        return normalized in {"yes", "confirm", "ok", "haan", "ha", "yes please", "confirm karo"}