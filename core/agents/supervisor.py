import os
import json
import sys
import io
from pydantic import BaseModel, Field

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    # Check if already reconfigured to avoid recursion or errors
    if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except:
            pass

from typing import Literal
from core.state import AgentState
from langgraph.graph import StateGraph, END
from core.agents.universal_agent import universal_agent_node
from core.agents.socratic_agent import socratic_agent_node
from core.agents.reporting_agent import reporting_agent_node
from core.graph import load_file_node, extract_skill_node, save_skill_node 
from core.utils.z_research import ZResearch
from core.utils.observability import obs
from core.agents.firecrawl_agent import firecrawl_node
from core.agents.executive_ops_agent import executive_ops_node
from core.agents.coding_crew import developer_node, auditor_node, researcher_node, synthesis_node as tech_synthesis_node
from core.agents.parallel_crew import researcher_perspective, critic_perspective, brainstormer_perspective, practical_perspective, analyst_perspective
from core.agents.synthesizer import synthesis_node as general_synthesis_node
from core.services.telegram_service import telegram_service
from core.agents.mcp_agent import mcp_agent_node
from core.agents.n8n_skill_agent import n8n_skill_node
from core.utils.llm_manager import LLMManager
from core.agents.ops_agent import ops_node
from core.agents.wellness_agent import wellness_agent_node
from core.agents.scheduler_agent import scheduler_node
from core.agents.verifier_agent import verifier_node
from core.agents.scholar_agent import scholar_agent_node
from core.agents.eq_agent import eq_agent_node
from core.agents.skill_extractor_agent import skill_extractor_node
from core.agents.commute_logic_agent import commute_agent_node
from core.agents.trendscout_agent import trendscout_node
from core.agents.mimi_router import mimi_router_node
from core.agents.summarize_agent import summarize_agent_node
from core.utils.priority_memory import priority_memory
from core.utils.interaction_logger import logger as interaction_logger
from core.agents.growth_agent import growth_agent_node
from core.agents.utils_nodes import (
    memory_retrieval_node, finalize_session_node, priority_lookup_node,
    mimi_logging_node, token_tracker_node, readiness_check_node,
    retry_increment_node
)
from core.agents.content_evaluator import content_evaluator_node
from core.agents.memory_nodes import memory_compaction_node
import asyncio

class HandoffIntent(BaseModel):
    target: Literal[
        "research", "tech", "growth", "bank", "academic", 
        "legal", "mimi", "cos", "heritage", "wellness", 
        "advisor", "learning", "browser", "mcp", "automation", "intel", "trend"
    ] = Field(description="The internal key for the agent to hand off to.")
    reasoning: str = Field(description="Brief explanation of why this agent was chosen for the handoff.")

class RoutingIntent(BaseModel):
    category: Literal[
        "research", "bank", "tech", "growth", "academic", 
        "advisor", "legal", "mimi", "cos", "heritage", 
        "wellness", "learning", "browser", "mcp", "automation", "commute", "trend"
    ] = Field(description="The category that best matches the user's request.")
    reasoning: str = Field(description="Brief explanation of why this category was chosen.")

class SupervisorAgent:
    # ... (init and load_prompts remain same)
    def __init__(self):
        # KnowledgeAgent is no longer directly used here, as universal_agent_node handles it
        self.researcher = ZResearch()
        self.prompts = self._load_prompts()

    def _load_prompts(self):
        p = {}
        # Normalize the base path to handle mixed slashes on Windows
        root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
        prompt_dir = os.path.join(root_dir, "prompts")
        
        if os.path.exists(prompt_dir):
            for f in os.listdir(prompt_dir):
                if f.endswith(".md"):
                    file_path = os.path.join(prompt_dir, f)
                    with open(file_path, 'r', encoding='utf-8') as file:
                        p[f.replace(".md", "")] = file.read()
        return p

    def route_request(self, user_input: str, memory_context: list = None) -> str:
        """
        Determines intent using structured output via Gemini Flash.
        """
        print(f"  [Supervisor] Determining routing intent for: {user_input[:50]}...")
        
        memory_str = "\n".join([f"- {m}" for m in memory_context]) if memory_context else "None"
        
        prompt = f"""
        Analyze the user's request and categorize it correctly.
        
        IMPORTANT RULE: If the request is a simple greeting (e.g., "xin chào", "hello", "hi", "chào"), casual chat, or a broad personal question with no specific domain, ALWAYS return "learning".
        
        Relevant Context from Long-term Memory:
        {memory_str}

        Categories:
        - learning: Simple greetings, casual chat, broad personal questions, general AI Assistant queries.
        - research: PhD research, academic papers, mentorship (Local files).
        - browser: Live web search, GitHub repos, NPM news, real-time info (Web Access).
        - bank: Banking strategy, SME, NPS.
        - tech: Programming, React, Vue, UI components, code, debug, refactor (NOT greetings).
        - growth: Branding, LinkedIn, sales.
        - mimi: RESERVED for Mimi's dedicated HomeTutor web app ONLY. DO NOT route here from Telegram or general chat. If the user asks about Grade 7 Science or children's tutoring via Telegram, route to "academic" instead.
        - academic: Support for secondary science curriculum modules and general tutoring if Mimi agent is not explicitly requested.
        - wellness: Health, mindset, sleep.
        - cos: Daily scheduling, task management, "lịch hôm nay", family ops, Executive operations.
        - automation: External app actions using n8n (Google Calendar, Notion, Slack, LinkedIn, etc.).
        - mcp: Standardized external tools (GitHub, Slack, Custom API).
        - commute: Use for requests related to the 4-hour daily bus travel, commute gamification, voice-to-insight during travel, or "Commute Mode".
        - trend: KOL updates, industry trends, daily briefing, xu hướng mới, mindset changer, cập nhật từ chuyên gia, AI trends, accounting/finance trends, education trends.

        Request: {user_input}

        Return your answer as a raw JSON string matching this schema:
        {{
            "category": "category_name",
            "reasoning": "brief explanation"
        }}
        """
        
        try:
            # Using L2/Medium complexity for routing to ensure reliability with Opus-aware thinking
            raw_response = self.researcher.query(prompt, complexity="L2")
            if raw_response.startswith("ERROR"):
                print(f"  [Supervisor] LLM Query failed with error string. Triggering fallback.")
                raise ValueError("LLM Error String encountered")

            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0].strip()
            
            # Find first { and last } to handle stray text
            start = raw_response.find("{")
            end = raw_response.rfind("}")
            if start != -1 and end != -1:
                raw_response = raw_response[start:end+1]
            
            data = json.loads(raw_response)
            intent = RoutingIntent(**data)
            print(f"  [Supervisor] Chose category: {intent.category} | Reason: {intent.reasoning}")
            return intent.category
        except Exception as e:
            print(f"  [Supervisor] Error in structured routing: {e}. Falling back.")
            user_input_safe = str(user_input).lower() if user_input else ""
            if user_input_safe.startswith("mimi:"):
                return "academic"
            if any(word in user_input_safe for word in ["live", "search", "web", "internet", "cập nhật"]):
                return "browser"
            if any(word in user_input_safe for word in ["calendar", "notion", "lịch", "ghép", "meeting", "hẹn", "automation", "n8n", "task"]):
                return "cos" # Prefer COS for schedule/tasks rather than empty automation
            if any(word in user_input_safe for word in ["skill", "extract", "code", "react", "component", "debug", "dev"]):
                return "tech"
            return "learning"

    def determine_handoff_target(self, query: str, metadata: dict = None) -> str:
        """
        Dynamically determines the best handoff target using LLM reasoning.
        """
        print(f"  [Supervisor] Dynamically resolving handoff for: {query[:50]}...")
        
        meta_str = json.dumps(metadata) if metadata else "None"
        
        prompt = f"""
        You are the Swarm Orchestrator. An agent has requested a handoff.
        
        REQUEST/CONTEXT: {query}
        HANDOFF METADATA: {meta_str}
        
        Available Agent Keys:
        - research: Academic/PhD research, complex fact-gathering.
        - tech: Software development, debugging, architecture.
        - growth: Branding, marketing, creative brainstorming.
        - bank: Banking strategy, SME finance.
        - academic: Teaching, student mentorship.
        - legal: Legal documents, tax, accounting.
        - mimi: Socratic tutoring for children.
        - cos: Executive operations, scheduling.
        - heritage: Eastern philosophy, family history.
        - wellness: Health, mindset, fitness.
        - advisor: Strategic business consulting.
        - learning: Casual chat, general knowledge.
        - browser: Real-time web search.
        - automation: n8n/External task execution.
        - intel: Generating an intelligence report/summary.
        - trend: KOL updates, industry trends, daily briefing from experts.
        
        Return your answer as a raw JSON string matching this schema:
        {{
            "target": "agent_key",
            "reasoning": "why this agent is the best fit"
        }}
        """
        
        try:
            raw_response = self.researcher.query(prompt, complexity="L2")
            if not raw_response:
                print("  [Supervisor] No response from LLM for handoff. Falling back to 'learning'.")
                return "learning"

            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0].strip()
            
            data = json.loads(raw_response)
            intent = HandoffIntent(**data)
            print(f"  [Supervisor] Dynamic Handoff -> {intent.target} | Reason: {intent.reasoning}")
            return intent.target
        except Exception as e:
            print(f"  [Supervisor] Error in dynamic handoff: {e}. Falling back to 'learning'.")
            return "learning"

def router_node(state: AgentState):
    """Refined router node with PostHog analytics."""
    messages = state.get("messages") or []
    print(f"  [DEBUG] router_node messages (raw): {messages}")
    
    # Find the last message that is NOT a system message
    user_input = ""
    for msg in reversed(messages):
        if msg and isinstance(msg, str) and not msg.startswith("System"):
            user_input = msg
            break
            
    if not user_input:
        user_input = messages[-1] if messages else "No Input Provided"
    
    if not isinstance(user_input, str):
        user_input = str(user_input)
        
    user_id = state.get("user_id", "default_user")
    
    # Allow manual override via state
    if state.get("routing_category") and not state.get("routing_category").startswith("critique_"):
        existing_route = state.get("routing_category")
        print(f"  [Supervisor] Using pre-set routing category: {existing_route}")
        return {"routing_category": existing_route, "messages": [f"System: Using manual route: {existing_route}"]}

    supervisor = SupervisorAgent()
    memory = state.get("long_term_memory", [])
    route = supervisor.route_request(user_input, memory_context=memory)
    
    # Phase 4: Observability
    obs.track_event(user_id, "agent_routed", {
        "category": route,
        "input_length": len(user_input)
    })
    
    return {"routing_category": route, "messages": [f"System: Routing to {route}"]}
from core.utils.memory_manager import memory_manager
from core.utils.llm_manager import ContextPruner

def daily_intel_node(state: AgentState):
    """Strategy C: Synthesis of multi-domain intelligence."""
    llm = LLMManager()
    messages = state.get("messages", [])
    summary_context = "\n".join(messages[-10:]) # last 10 steps
    
    prompt = f"""
    You are the Chief Intelligence Officer. 
    Review the following multi-agent conversation and synthesize a 'Daily Intel Report'.
    
    CONTEXT:
    {summary_context}
    
    MISSION:
    1. Extract key facts and decisions.
    2. Identify cross-domain dependencies.
    3. Suggest next strategic steps for the user.
    
    Format:
    # 🕵️ Intel Report
    ## 🎯 Key Facts
    ## 🔗 Dependencies
    ## 🚀 Recommendations
    """
    print("  [Intel Agent] Synthesizing report...")
    report = llm.query(prompt, complexity="L3")
    return {"messages": [f"Intel Agent: {report}"]}

from core.agents.browser_agent import browser_agent_node

from core.agents.critic_agent import critic_node

from skills.wellness.oura_client import OuraClient


def build_supervisor_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("ops_guard", ops_node)
    workflow.add_node("readiness_check", readiness_check_node)
    workflow.add_node("memory_retrieval", memory_retrieval_node)
    workflow.add_node("memory_compaction", memory_compaction_node)
    workflow.add_node("supervisor", router_node)
    workflow.add_node("token_tracker", token_tracker_node)
    workflow.add_node("finalize", finalize_session_node)
    
    # Specialized Nodes
    workflow.add_node("research_node", universal_agent_node)
    workflow.add_node("browser_node", browser_agent_node)
    workflow.add_node("firecrawl_node", firecrawl_node)
    
    workflow.add_node("bank_node", universal_agent_node)
    workflow.add_node("growth_node", growth_agent_node)
    workflow.add_node("academic_node", universal_agent_node)
    workflow.add_node("legal_node", universal_agent_node)
    workflow.add_node("cos_node", executive_ops_node) # Fixed Wiring
    workflow.add_node("heritage_node", universal_agent_node)
    workflow.add_node("wellness_node", wellness_agent_node)
    workflow.add_node("advisor_node", universal_agent_node)
    workflow.add_node("learning_node", universal_agent_node)
    workflow.add_node("executive_ops_node", executive_ops_node)
    workflow.add_node("intel_report", daily_intel_node)
    
    # Coding Crew (Parallel Branch)
    workflow.add_node("developer", developer_node)
    workflow.add_node("auditor", auditor_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("synthesis", tech_synthesis_node)
    
    workflow.add_node("tech_load", load_file_node)
    workflow.add_node("tech_extract", extract_skill_node)
    workflow.add_node("tech_save", save_skill_node)
    
    # Phase 6: Generalized Parallel Perspectives
    workflow.add_node("researcher_p", researcher_perspective)
    workflow.add_node("critic_p", critic_perspective)
    workflow.add_node("brainstormer_p", brainstormer_perspective)
    workflow.add_node("practical_p", practical_perspective)
    workflow.add_node("analyst_p", analyst_perspective)
    workflow.add_node("general_synthesis", general_synthesis_node)

    workflow.add_node("mimi_tutor", socratic_agent_node)
    workflow.add_node("mimi_summarizer", summarize_agent_node)
    workflow.add_node("mimi_router", mimi_router_node)
    workflow.add_node("scholar_tutor", scholar_agent_node)
    workflow.add_node("parent_reporting", reporting_agent_node)
    workflow.add_node("mcp_node", mcp_agent_node)
    workflow.add_node("n8n_skill_node", n8n_skill_node)
    workflow.add_node("scheduler_node", scheduler_node)
    workflow.add_node("priority_lookup", priority_lookup_node)
    workflow.add_node("mimi_logger", mimi_logging_node)
    
    # Phase 5: Quality Guard Node
    workflow.add_node("critic", critic_node)
    workflow.add_node("retry_increment", retry_increment_node)
    workflow.add_node("verifier", verifier_node)
    
    workflow.add_node("eq_sensing", eq_agent_node)
    workflow.add_node("skill_extractor", skill_extractor_node)
    workflow.add_node("commute_node", commute_agent_node)
    workflow.add_node("trendscout_node", trendscout_node)
    workflow.add_node("content_curator_critic", content_evaluator_node)
    
    workflow.set_entry_point("ops_guard")
    workflow.add_edge("ops_guard", "eq_sensing")
    workflow.add_edge("eq_sensing", "readiness_check")
    workflow.add_edge("readiness_check", "memory_retrieval")
    workflow.add_edge("memory_retrieval", "memory_compaction")
    workflow.add_edge("memory_compaction", "priority_lookup")
    workflow.add_edge("priority_lookup", "supervisor")
    
    def decide_route(state):
        route = state.get("routing_category")
        messages = state.get("messages", [])
        readiness = state.get("readiness_score", 100)
        
        # BIO-ADAPTIVE ROUTING: If readiness is critical (< 65), pivot to Wellness/Stoic
        # EXEMPTION: Mimi's educational tutoring should NEVER be pivoted to wellness.
        if readiness < 65 and route in ["tech", "research", "intel"] and not route.startswith("mimi"):
            print(f"  [Supervisor] Readiness Low ({readiness}). Pivoting from {route} to wellness/recovery.")
            return ["wellness_node"]

        print(f"  [DEBUG] decide_route: route={route}, messages_len={len(messages) if messages else 'None'}")
        
        if route == "tech": 
            # If user asks to extract/save/load, use file logic. Else use Parallel Crew.
            if not messages or not isinstance(messages[-1], str):
                print("  [DEBUG] decide_route: messages is None, empty, or not a string list!")
                return ["learning_node"]
            
            user_input = messages[-1].lower()
            if any(w in user_input for w in ["extract", "save skill", "load file"]):
                return ["tech_load"]
            return ["developer", "auditor", "researcher"]
            
        if route == "research":
            return ["researcher_p", "critic_p", "analyst_p"]
            
        if route == "growth":
            return ["brainstormer_p", "practical_p", "researcher_p"]

        # Token Optimization: Collapse parallel branches if over budget
        token_budget = state.get("token_tracker", 0)
        SOFT_LIMIT = 5000 # Example soft limit for parallelization
        
        if token_budget > SOFT_LIMIT:
            print(f"  [System] Token budget low ({token_budget}). Collapsing parallel branches.")
            if route in ["tech", "research", "growth"]:
                return ["learning_node"] # Use a single universal agent instead of parallel crew

        mapping = {
            "bank": ["bank_node"], 
            "academic": ["scholar_tutor"], 
            "legal": ["legal_node"],
            "mimi": ["mimi_router"],
            "mimi_theory": ["mimi_summarizer"],
            "mimi_exercise": ["mimi_tutor"],
            "mimi_general": ["mimi_summarizer"],
            "cos": ["executive_ops_node"],
            "heritage": ["heritage_node"], 
            "wellness": ["wellness_node"], 
            "advisor": ["advisor_node"],
            "learning": ["learning_node"], # Fix: Was routing to scholar_tutor incorrectly
            "browser": ["firecrawl_node"],
            "mcp": ["mcp_node"],
            "automation": ["n8n_skill_node"],
            "commute": ["commute_node"],
            "trend": ["trendscout_node"]
        }
        
        # Custom Logic for Scheduler Optimization
        if route == "cos":
            if any(w in str(messages[-1]).lower() for w in ["tối ưu", "optimize", "sắp xếp lại", "rearrange"]):
                print("  [Supervisor] Routing to scheduler_node for optimization.")
                return ["scheduler_node"]
            return ["executive_ops_node"]

        if route == "priority_hit":
            return ["mimi_logger"] # Go straight to logging then END (finalize)

        return mapping.get(route, ["learning_node"])
            
    workflow.add_conditional_edges(
        "supervisor",
        decide_route
    )
    
    # Joint point for parallel branch
    workflow.add_edge("developer", "synthesis")
    workflow.add_edge("auditor", "synthesis")
    workflow.add_edge("researcher", "synthesis")
    # REMOVED: workflow.add_edge("synthesis", "verifier") -> now handled exclusively by after_synthesis
    
    # Joint points for Generalized Parallel
    workflow.add_edge("researcher_p", "general_synthesis")
    workflow.add_edge("critic_p", "general_synthesis")
    workflow.add_edge("analyst_p", "general_synthesis")
    workflow.add_edge("brainstormer_p", "general_synthesis")
    workflow.add_edge("practical_p", "general_synthesis")
    
    
    # synthesis and general_synthesis flow through intermediate_nodes -> token_tracker -> critic
    
    workflow.add_edge("tech_load", "tech_extract")
    workflow.add_edge("tech_extract", "tech_save")
    
    # All specialized outputs go to tracker then CRITIC
    intermediate_nodes_all = [
        "research_node", "firecrawl_node", "browser_node", "bank_node", 
        "growth_node", "academic_node", "legal_node", "executive_ops_node", 
        "heritage_node", "wellness_node", "advisor_node", "learning_node", 
        "tech_save", "mimi_tutor", "mimi_summarizer", "scholar_tutor", 
        "parent_reporting", "synthesis", "general_synthesis", "mcp_node", 
        "scheduler_node", "verifier", "commute_node", "trendscout_node",
        "intel_report"
    ]
    # For handoff logic iteration
    intermediate_nodes = intermediate_nodes_all
    
    # Add mimi agents edges to logger
    # REMOVED direct edges to mimi_logger -> now handled via after_mimi_tutor
    workflow.add_edge("mimi_logger", "token_tracker")

    workflow.add_edge("growth_node", "content_curator_critic")

    workflow.add_edge("token_tracker", "critic")
    
    # Strategy C: Handoff Resolver
    def resolve_handoff(state: AgentState):
        target = state.get("handoff_target")
        # metadata = state.get("handoff_metadata") # Can't use in transition directly if needing LLM
        
        # Mapping of common keys to node names
        mapping = {
            "research": "research_node",
            "tech": "developer",
            "growth": "researcher_p",
            "bank": "bank_node",
            "academic": "scholar_tutor",
            "legal": "legal_node",
            "mimi": "mimi_tutor",
            "scholar": "scholar_tutor",
            "cos": "executive_ops_node",
            "heritage": "heritage_node",
            "wellness": "wellness_node",
            "advisor": "advisor_node",
            "learning": "scholar_tutor",
            "intel": "intel_report",
            "browser": "firecrawl_node",
            "mcp": "mcp_node",
            "automation": "n8n_skill_node",
            "trend": "trendscout_node"
        }

        # If a handoff was requested
        if target:
            if target in intermediate_nodes or target in ["developer", "researcher_p"]:
                return target
            if target in mapping:
                return mapping[target]
            
            # Note: We can't call LLM inside a transition function easily 
            # if we want to follow LangGraph best practices (transitions should be deterministic or based on state).
            # For now, we'll route to 'supervisor' (the router) to handle the handoff logic if it's unknown.
            return "supervisor"

        # DEFAULT NEXT STEPS (if no handoff)
        # Some nodes have specific sequels
        source_node = state.get("routing_category", "") # This isn't reliable for node name
        # We can't easily know the 'current' node name here without passing it or state hack
        # Instead, we define specialist rules
        
        return "token_tracker"

    # Define dedicated joint functions for specialist nodes
    def after_synthesis(state: AgentState):
        if state.get("handoff_target"): return resolve_handoff(state)
        return "verifier"

    def after_verifier(state: AgentState):
        if state.get("handoff_target"): return resolve_handoff(state)
        return "token_tracker"
    
    def after_mimi_tutor(state: AgentState):
        if state.get("handoff_target"): return resolve_handoff(state)
        return "mimi_logger"

    # Standard handoff for most nodes
    for node in [
        "research_node", "firecrawl_node", "browser_node", "bank_node", 
        "academic_node", "legal_node", "executive_ops_node", "heritage_node", 
        "wellness_node", "advisor_node", "learning_node", "tech_save", 
        "scholar_tutor", "parent_reporting", "general_synthesis", 
        "mcp_node", "scheduler_node", "commute_node", "trendscout_node",
        "intel_report"
    ]:
        workflow.add_conditional_edges(node, resolve_handoff)

    # Specialist joint nodes
    workflow.add_conditional_edges("synthesis", after_synthesis)
    workflow.add_conditional_edges("verifier", after_verifier)
    workflow.add_conditional_edges("mimi_tutor", after_mimi_tutor)
    workflow.add_conditional_edges("mimi_summarizer", after_mimi_tutor) # both use mimi_logger
    
    workflow.add_edge("intel_report", "token_tracker")
    workflow.add_edge("token_tracker", "critic")
    
    # Phase 5: Conditional Routing for Critic
    def decide_critique(state):
        decision = state.get("routing_category") 
        retry_count = state.get("retry_count", 0)
        execution_status = state.get("execution_status")
        
        # Self-Healing Loop: retry if critic says REVISE OR if execution FAILED
        if (decision == "critique_revise" or execution_status == "failure") and retry_count < 2:
            return "retry_increment"
        
        # New loop for ContentCurator
        if decision == "revise_content" and retry_count < 2:
             return "retry_increment"

        return "finalize"

    def decide_content_quality(state):
        if not state.get("is_valid"):
            return "retry_increment" # Increment retry then back to supervisor
        return "token_tracker"

    workflow.add_conditional_edges(
        "content_curator_critic",
        decide_content_quality
    )

    workflow.add_conditional_edges(
        "critic",
        decide_critique
    )
    
    workflow.add_edge("retry_increment", "supervisor")
    workflow.add_edge("finalize", END)
    return workflow.compile()

if __name__ == "__main__":
    import sys
    async def test_routing():
        graph = build_supervisor_graph()
        query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "how do I use MCP to create a github issue?"
        print(f"--- Testing Supervisor Routing for: {query} ---")
        initial_state = {
            "messages": [query],
            "user_id": "test_user",
            "retry_count": 0,
            "is_valid": True
        }
        result = await graph.ainvoke(initial_state)
        print("\n--- Final Messages ---")
        for msg in result.get("messages", []):
            print(f"> {msg}")
        print(f"\nRouting Category: {result.get('routing_category')}")

    asyncio.run(test_routing())
