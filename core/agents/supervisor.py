import os
import json
import sys
import io
import asyncio
from typing import Literal, Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from core.state import AgentState
from langgraph.graph import StateGraph, END
from core.utils.input_sanitizer import sanitize_user_input
from core.utils.bot_logger import get_logger
from core.agents.planner_agent import PlannerAgent
from core.agents.reflection_agent import ReflectionAgent
from core.utils.memory_manager import memory_manager
from core.agents.intelligence_agent import intelligence_node
from core.agents.multimodal_agent import multimodal_node
from core.agents.iching_agent import iching_agent_node
from core.agents.council_agent import council_agent_node
from core.agents.specialized_knowledge_agent import specialized_knowledge_node

logger = get_logger("supervisor")

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except Exception:
            pass

# Lazy Load Wrappers for Nodes
def wrap_node(module_path, node_name):
    async def wrapper(state: AgentState):
        import importlib
        mod = importlib.import_module(module_path)
        node_func = getattr(mod, node_name)
        if asyncio.iscoroutinefunction(node_func):
            return await node_func(state)
        result = node_func(state)
        if asyncio.iscoroutine(result):
            return await result
        return result
    return wrapper

# Specialized wrappers for renamed nodes
def tech_synthesis_wrapper(state: AgentState):
    from core.agents.coding_crew import synthesis_node
    return synthesis_node(state)

def general_synthesis_wrapper(state: AgentState):
    from core.agents.synthesizer import synthesis_node
    return synthesis_node(state)

def admin_node_wrapper(state: AgentState):
    from core.agents.admin_agent import admin_agent_node
    return admin_agent_node(state)

class HandoffIntent(BaseModel):
    target: Literal[
        "research", "tech", "growth", "bank", "academic", 
        "legal", "mimi", "cos", "heritage", "wellness", 
        "advisor", "learning", "browser", "mcp", "automation", 
        "intel", "trend", "multimodal", "engineering", "medicine", 
        "qa", "precision_health", "ethics", "memory", "synthesis", "persona", "admin", "council"
    ] = Field(description="The internal key for the agent to hand off to.")
    reasoning: str = Field(description="Brief explanation of why this agent was chosen for the handoff.")

class RoutingIntent(BaseModel):
    category: Literal[
        "academic", "business", "wellness", "tech", "research", "ops", 
        "growth", "heritage", "automation", "admin", "multimodal", "general",
        "fast_path"
    ] = Field(description="The primary category that best matches the user's request.")
    reasoning: str = Field(description="Brief explanation of why this category was chosen.")

class SupervisorAgent:
    """
    Central orchestrator agent responsible for analyzing user intent 
    and routing requests to the appropriate specialized sub-agents.
    """
    def __init__(self) -> None:
        # KnowledgeAgent is no longer directly used here, as universal_agent_node handles it
        from core.utils.z_research import ZResearch
        self.researcher: ZResearch = ZResearch()
        self.prompts: Dict[str, str] = self._load_prompts()

    def _load_prompts(self):
        p = {}
        # Normalize the base path to handle mixed slashes on Windows
        root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "../.."))
        prompt_dir = os.path.join(root_dir, "prompts")
        
        if os.path.exists(prompt_dir):
            for f in os.listdir(prompt_dir):
                if f.endswith(".md"):
                    file_path = os.path.join(prompt_dir, f)
                    with open(file_path, 'r', encoding='utf-8') as file:
                        p[f.replace(".md", "")] = file.read()
        return p

    async def route_request(self, user_input: str, memory_context: Optional[List[str]] = None) -> str:
        """
        Determines routing intent using structured output via LLM.
        Enhanced with time-of-day awareness and conversation context to prevent misroutes.
        """
        user_input = sanitize_user_input(user_input)
        from datetime import datetime
        print(f"  [Supervisor] Determining routing intent for: {user_input[:50]}...")
        
        memory_str = "\n".join([f"- {m}" for m in memory_context]) if memory_context else "None"
        
        # Time-of-day context for smarter routing
        now = datetime.now()
        time_context = f"Current time: {now.strftime('%H:%M')} ({now.strftime('%A')})"
        
        # Get recent routing history to prevent repeated misroutes
        routing_history = ""
        try:
            from core.services.conversation_store import conversation_store
            recent_routes = await conversation_store.get_last_routing("default_user", n=3)
            if recent_routes:
                routing_history = f"Recent routing: {', '.join(recent_routes)}"
        except Exception:
            pass
        
        prompt_template = self.prompts.get("supervisor_routing", "Analyze the user's request and categorize it correctly.")
        prompt = prompt_template.format(
            time_context=time_context,
            routing_history=routing_history,
            memory_str=memory_str,
            user_input=user_input
        )
        
        try:
            raw_response = self.researcher.query(prompt, complexity="L2")
            if raw_response.startswith("ERROR"):
                print(f"  [Supervisor] LLM Query failed with error string. Triggering fallback.")
                raise ValueError("LLM Error String encountered")

            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0].strip()
            
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
            if any(word in user_input_safe for word in [
                "calendar", "notion", "lịch", "ghép", "meeting", "hẹn", 
                "automation", "n8n", "task", "hôm nay", "kế hoạch", "schedule",
                "làm gì", "báo cáo", "report", "ops", "executive"
            ]):
                return "cos"
            if any(word in user_input_safe for word in ["skill", "extract", "code", "react", "component", "debug", "dev"]):
                return "tech"
            if any(word in user_input_safe for word in ["trend", "xu hướng", "kol", "briefing"]):
                return "trend"
            if any(word in user_input_safe for word in ["chào", "hi", "hello", "tạm biệt", "mấy giờ"]):
                return "fast_path"
            return "learning"

    def determine_handoff_target(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Dynamically determines the best handoff target using LLM reasoning.
        """
        query = sanitize_user_input(query)
        print(f"  [Supervisor] Dynamically resolving handoff for: {query[:50]}...")
        
        meta_str = json.dumps(metadata) if metadata else "None"
        
        prompt_template = self.prompts.get("supervisor_handoff", "You are the Swarm Orchestrator. An agent has requested a handoff.")
        prompt = prompt_template.format(
            query=query,
            meta_str=meta_str
        )
        
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


async def router_node(state: AgentState):
    """Refined router node with Planner for L3 tasks."""
    messages = state.get("messages") or []
    user_input = messages[-1] if messages else ""
    
    # ... existing Skill Registry check ...
    from core.skills.skill_registry import skill_registry
    skill = skill_registry.find_match(user_input)
    if skill:
        return {"routing_category": "fast_path_complete", "messages": [f"Assistant: {skill.func(user_input)}"]}

    # Decide if we need a Planner
    if len(user_input) > 200 or "plan" in user_input.lower():
        planner = PlannerAgent()
        plan = await planner.generate_plan(user_input)
        return {
            "routing_category": "planned_execution",
            "execution_plan": plan.dict(),
            "messages": [f"System: Strategic plan generated. Executing..."]
        }

    supervisor = SupervisorAgent()
    route = await supervisor.route_request(user_input)
    return {"routing_category": route, "messages": [f"System: Primary route -> {route}"]}

async def reflection_node(state: AgentState):
    """Post-synthesis analysis to extract long-term lessons."""
    reflector = ReflectionAgent()
    messages = state.get("messages", [])
    if not messages: return {}
    
    last_interaction = json.dumps(messages[-2:] if len(messages) >= 2 else messages)
    log = await reflector.reflect(last_interaction)
    
    if log.suggested_memory:
        await memory_manager.archive_to_semantic(state.get("user_id", "default"), log.suggested_memory)
        
    return {"reflection_log": log.dict()}

def fast_path_node(state: AgentState):
    """Bypasses deep reasoning for trivial queries."""
    user_input = state["messages"][-1]
    from core.utils.llm_manager import LLMManager
    llm = LLMManager()
    
    prompt = f"Respond naturally to this simple greeting or query: {user_input}"
    response = llm.query(prompt, complexity="L1")
    return {"messages": [f"Assistant: {response}"], "routing_category": "fast_path_complete"}

def build_supervisor_graph():
    workflow = StateGraph(AgentState)
    
    # Static tools that are fast
    from core.utils.memory_manager import memory_manager
    from core.utils.llm_manager import ContextPruner
    
    # Load nodes lazily
    ops_node = wrap_node("core.agents.ops_agent", "ops_node")
    readiness_check_node = wrap_node("core.agents.utils_nodes", "readiness_check_node")
    memory_retrieval_node = wrap_node("core.agents.utils_nodes", "memory_retrieval_node")
    memory_compaction_node = wrap_node("core.agents.memory_nodes", "memory_compaction_node")
    token_tracker_node = wrap_node("core.agents.utils_nodes", "token_tracker_node")
    finalize_session_node = wrap_node("core.agents.utils_nodes", "finalize_session_node")
    priority_lookup_node = wrap_node("core.agents.utils_nodes", "priority_lookup_node")
    
    universal_agent_node = wrap_node("core.agents.universal_agent", "universal_agent_node")
    browser_agent_node = wrap_node("core.agents.browser_agent", "browser_agent_node")
    firecrawl_node = wrap_node("core.agents.firecrawl_agent", "firecrawl_node")
    growth_agent_node = wrap_node("core.agents.growth_agent", "growth_agent_node")
    executive_ops_node = wrap_node("core.agents.executive_ops_agent", "executive_ops_node")
    wellness_agent_node = wrap_node("core.agents.wellness_agent", "wellness_agent_node")
    iching_agent_node = wrap_node("core.agents.iching_agent", "iching_agent_node")
    developer_node = wrap_node("core.agents.coding_crew", "developer_node")
    auditor_node = wrap_node("core.agents.coding_crew", "auditor_node")
    researcher_node = wrap_node("core.agents.coding_crew", "researcher_node")
    
    load_file_node = wrap_node("core.graph", "load_file_node")
    extract_skill_node = wrap_node("core.graph", "extract_skill_node")
    save_skill_node = wrap_node("core.graph", "save_skill_node")
    
    researcher_perspective = wrap_node("core.agents.parallel_crew", "researcher_perspective")
    critic_perspective = wrap_node("core.agents.parallel_crew", "critic_perspective")
    brainstormer_perspective = wrap_node("core.agents.parallel_crew", "brainstormer_perspective")
    practical_perspective = wrap_node("core.agents.parallel_crew", "practical_perspective")
    analyst_perspective = wrap_node("core.agents.parallel_crew", "analyst_perspective")
    
    socratic_agent_node = wrap_node("core.agents.socratic_agent", "socratic_agent_node")
    summarize_agent_node = wrap_node("core.agents.summarize_agent", "summarize_agent_node")
    mimi_router_node = wrap_node("core.agents.mimi_router", "mimi_router_node")
    scholar_agent_node = wrap_node("core.agents.scholar_agent", "scholar_agent_node")
    reporting_agent_node = wrap_node("core.agents.reporting_agent", "reporting_agent_node")
    mcp_agent_node = wrap_node("core.agents.mcp_agent", "mcp_agent_node")
    n8n_skill_node = wrap_node("core.agents.n8n_skill_agent", "n8n_skill_node")
    scheduler_node = wrap_node("core.agents.scheduler_agent", "scheduler_node")
    mimi_logging_node = wrap_node("core.agents.utils_nodes", "mimi_logging_node")
    critic_node = wrap_node("core.agents.critic_agent", "critic_node")
    retry_increment_node = wrap_node("core.agents.utils_nodes", "retry_increment_node")
    verifier_node = wrap_node("core.agents.verifier_agent", "verifier_node")
    eq_agent_node = wrap_node("core.agents.eq_agent", "eq_agent_node")
    skill_extractor_node = wrap_node("core.agents.skill_extractor_agent", "skill_extractor_node")
    commute_agent_node = wrap_node("core.agents.commute_logic_agent", "commute_agent_node")
    trendscout_node = wrap_node("core.agents.trendscout_agent", "trendscout_node")
    content_evaluator_node = wrap_node("core.agents.content_evaluator", "content_evaluator_node")
    council_node = wrap_node("core.agents.council_agent", "council_agent_node")

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
    workflow.add_node("admin_node", admin_node_wrapper)
    workflow.add_node("iching_node", iching_agent_node)
    workflow.add_node("council_node", council_node)
    workflow.add_node("fast_path_node", fast_path_node)
    
    multimodal_agent_node = wrap_node("core.agents.multimodal_agent", "multimodal_node")
    workflow.add_node("multimodal_node", multimodal_agent_node)
    workflow.add_node("engineering_node", universal_agent_node)
    workflow.add_node("medicine_node", universal_agent_node)
    workflow.add_node("qa_node", universal_agent_node)
    workflow.add_node("ethics_node", universal_agent_node)
    workflow.add_node("synthesis_node", universal_agent_node)
    workflow.add_node("persona_node", universal_agent_node)
    workflow.add_node("memory_node", universal_agent_node)
    
    # Coding Crew (Parallel Branch)
    workflow.add_node("developer", developer_node)
    workflow.add_node("auditor", auditor_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("synthesis", tech_synthesis_wrapper)
    
    workflow.add_node("tech_load", load_file_node)
    workflow.add_node("tech_extract", extract_skill_node)
    workflow.add_node("tech_save", save_skill_node)
    
    # Phase 6: Generalized Parallel Perspectives
    workflow.add_node("researcher_p", researcher_perspective)
    workflow.add_node("critic_p", critic_perspective)
    workflow.add_node("brainstormer_p", brainstormer_perspective)
    workflow.add_node("practical_p", practical_perspective)
    workflow.add_node("analyst_p", analyst_perspective)
    workflow.add_node("general_synthesis", general_synthesis_wrapper)

    workflow.add_node("specialized_knowledge", specialized_knowledge_node)
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
    workflow.add_node("intel_report", intelligence_node)
    workflow.add_node("multimodal_node", multimodal_node)
    workflow.add_node("council_node", council_agent_node)
    
    workflow.set_entry_point("ops_guard")
    workflow.add_edge("ops_guard", "eq_sensing")
    workflow.add_edge("eq_sensing", "readiness_check")
    workflow.add_edge("readiness_check", "memory_retrieval")
    workflow.add_edge("memory_retrieval", "memory_compaction")
    workflow.add_edge("memory_compaction", "priority_lookup")
    workflow.add_edge("priority_lookup", "supervisor")
    workflow.add_node("reflection", reflection_node)
    def decide_route(state: AgentState):
        route = state.get("routing_category")
        
        # TIER 2: SPECIALIST SUB-ROUTING
        mapping = {
            "academic": ["specialized_knowledge"],
            "business": ["specialized_knowledge"], 
            "wellness": ["specialized_knowledge"],
            "tech": ["developer", "auditor", "researcher"],
            "research": ["researcher_p", "critic_p", "analyst_p"],
            "growth": ["brainstormer_p", "practical_p", "researcher_p"],
            "ops": ["specialized_knowledge"],
            "heritage": ["specialized_knowledge"],
            "automation": ["n8n_skill_node"],
            "admin": ["admin_node"],
            "multimodal": ["multimodal_node"],
            "general": ["specialized_knowledge"],
            "fast_path": ["fast_path_node"],
            "fast_path_complete": ["finalize"],
            "planned_execution": ["developer"] 
        }
        
        return mapping.get(route, ["specialized_knowledge"])
            
    workflow.add_conditional_edges(
        "supervisor",
        decide_route
    )
    
    # Joint point for parallel branch
    workflow.add_edge("tech_load", "tech_extract")
    workflow.add_edge("tech_extract", "tech_save")
    
    def decide_coding_next(state):
        if state.get("is_valid") is False and state.get("retry_count", 0) < 2:
            return "retry"
        return "synthesis"

    workflow.add_conditional_edges(
        "auditor",
        decide_coding_next,
        {
            "retry": "retry_increment",
            "synthesis": "synthesis"
        }
    )
    workflow.add_edge("researcher", "synthesis")
    
    # ---------------------------------------------------------
    # DYNAMIC TEAM ASSEMBLY (Phase 4 Upgrade)
    # ---------------------------------------------------------
    def dynamic_team_resolver(state: AgentState):
        """
        Queries LLM to pick multiple specialized agents for a complex task.
        """
        user_input = state.get("messages", [""])[-1]
        print(f"  [Supervisor] Dynamically assembling team for: {user_input[:50]}...")
        
        from core.utils.llm_manager import LLMManager
        llm = LLMManager()
        
        prompt = f"""
        You are the Dynamic Team Orchestrator. Given the user request, pick 1-3 best sub-agents to solve it.
        
        REQUEST: {user_input}
        
        Available Agents:
        - developer: Write/Fix code.
        - researcher_p: Academic/Deep research.
        - wellness_node: Health/Fitness.
        - scholar_tutor: Academic subjects (K-12).
        - executive_ops_node: Scheduling/Task management.
        - browser_node: Live web search.
        
        Return only a JSON list of node names, e.g., ["developer", "researcher_p"].
        """
        try:
            res = llm.query(prompt, complexity="L1")
            import json
            team = json.loads(res.strip('`').replace('json\n', ''))
            return team if isinstance(team, list) else ["learning_node"]
        except:
            return ["learning_node"]

    # All specialized outputs go to tracker then CRITIC
    intermediate_nodes_all = [
        "research_node", "firecrawl_node", "browser_node", "specialized_knowledge",
        "tech_save", "mimi_router", "mimi_summarizer", 
        "parent_reporting", "synthesis", "general_synthesis", "mcp_node", 
        "scheduler_node", "verifier", "commute_node", "trendscout_node",
        "intel_report", "multimodal_node", "admin_node", "council_node"
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
            "bank": "specialized_knowledge",
            "academic": "specialized_knowledge",
            "legal": "specialized_knowledge",
            "mimi": "specialized_knowledge",
            "scholar": "specialized_knowledge",
            "cos": "specialized_knowledge",
            "heritage": "specialized_knowledge",
            "wellness": "specialized_knowledge",
            "advisor": "specialized_knowledge",
            "learning": "specialized_knowledge",
            "intel": "intel_report",
            "browser": "firecrawl_node",
            "mcp": "mcp_node",
            "automation": "n8n_skill_node",
            "trend": "trendscout_node",
            "multimodal": "multimodal_node",
            "engineering": "specialized_knowledge",
            "medicine": "specialized_knowledge",
            "qa": "specialized_knowledge",
            "precision_health": "specialized_knowledge",
            "ethics": "specialized_knowledge",
            "memory": "memory_node",
            "synthesis": "synthesis_node",
            "persona": "persona_node",
            "iching": "specialized_knowledge",
            "admin": "admin_node"
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

    # Standard handoff for most nodes (through critic)
    for node in [
        "research_node", "firecrawl_node", "browser_node", "specialized_knowledge",
        "tech_save", "mimi_router", "mimi_summarizer", 
        "parent_reporting", "general_synthesis", 
        "mcp_node", "scheduler_node", "commute_node", "trendscout_node",
        "multimodal_node", "synthesis_node", "persona_node", "memory_node", "admin_node"
    ]:
        workflow.add_conditional_edges(node, resolve_handoff)

    # Wellness & Fast Path bypasses the critic
    workflow.add_edge("wellness_node", "finalize")
    workflow.add_edge("fast_path_node", "finalize")

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
        
        # CONDITIONAL CRITIC: Skip for simple or already analyzed routes
        skip_critic_routes = ["fast_path", "general", "admin", "well-being"]
        if decision in skip_critic_routes and retry_count == 0:
            return "finalize"

        # Check response length - skip critic for very short responses
        messages = state.get("messages", [])
        if messages and len(str(messages[-1])) < 200 and retry_count == 0:
            return "finalize"

        # Self-Healing Loop: retry if critic says REVISE OR if execution FAILED
        if (decision == "critique_revise" or execution_status == "failure") and retry_count < 2:
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
    workflow.add_edge("finalize", "reflection")
    workflow.add_edge("reflection", END)

    # ---------------------------------------------------------
    # HUMAN-IN-THE-LOOP (HITL) CONFIGURATION
    # ---------------------------------------------------------
    # We interrupt before sensitive actions to allow user review.
    return workflow.compile(
        interrupt_before=["executive_ops_node", "tech_save", "admin_node"]
    )

if __name__ == "__main__":
    import sys
    async def test_routing():
        graph = build_supervisor_graph()
        query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "how do I use MCP to create a github issue?"
        logger.info(f"--- Testing Supervisor Routing for: {query} ---")
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
