import os
from typing import Literal
from langgraph.graph import StateGraph, END
from core.state import AgentState
from agents.preparer import PreparerAgent
from agents.navigator import NavigatorAgent
from agents.extractor import ExtractorAgent
from agents.overseer import OverseerAgent
from core.logger import get_logger

logger = get_logger(__name__)

# Keep one browser session per task_id so nodes share the same page.
_browser_sessions = {}

# Initialize agents
preparer = PreparerAgent()
navigator = NavigatorAgent()
extractor = ExtractorAgent()
overseer = OverseerAgent()

async def preparer_node(state: AgentState):
    logger.info(f"[{state.get('task_id')}] Graph: Entering Preparer node")
    from core.browser import BrowserManager
    task_id = state.get("task_id") or "UNKNOWN"
    browser_manager = BrowserManager()
    page = await browser_manager.start()
    _browser_sessions[task_id] = browser_manager
    
    result = await preparer.run(state, page)
    state.update(result)
    return state

async def extractor_node(state: AgentState):
    logger.info(f"[{state.get('task_id')}] Graph: Entering Extractor node")
    task_id = state.get("task_id") or "UNKNOWN"
    browser_manager = _browser_sessions.get(task_id)
    if not browser_manager or not getattr(browser_manager, "page", None):
        raise RuntimeError(f"[{task_id}] No active browser session found for Extractor node.")
    page = browser_manager.page
    
    result = await extractor.run(state, page)
    state.update(result)
    return state

async def navigator_node(state: AgentState):
    logger.info(f"[{state.get('task_id')}] Graph: Entering Navigator node")
    task_id = state.get("task_id") or "UNKNOWN"
    browser_manager = _browser_sessions.get(task_id)
    if not browser_manager or not getattr(browser_manager, "page", None):
        raise RuntimeError(f"[{task_id}] No active browser session found for Navigator node.")
    page = browser_manager.page

    result = await navigator.run(state, page)
    state.update(result)
    return state

async def overseer_node(state: AgentState):
    logger.info(f"[{state.get('task_id')}] Graph: Entering Overseer node")
    result = await overseer.run(state)
    state.update(result)
    return state

async def cleanup_node(state: AgentState):
    """
    Always close Playwright resources for this task.
    """
    task_id = state.get("task_id") or "UNKNOWN"
    logger.info(f"[{task_id}] Graph: Cleaning up browser session")
    browser_manager = _browser_sessions.pop(task_id, None)
    try:
        if browser_manager:
            await browser_manager.stop()
    except Exception as e:
        logger.warning(f"[{task_id}] Cleanup: failed to stop browser cleanly: {e}")
    return state

def should_continue(state: AgentState) -> Literal["extractor", "navigator", "__end__"]:
    """
    Conditional edge to decide whether to retry extraction or finish.
    """
    max_retries = int(os.getenv("MAX_EXTRACTION_RETRIES", 10))
    current_step = state.get("step_count", 0)
    is_valid = state.get("is_valid", False)
    next_action = (state.get("next_action") or "").strip().lower()
    
    logger.info(f"[{state.get('task_id')}] Graph: Evaluating continue. Valid={is_valid}, Step={current_step}/{max_retries}")
    
    if is_valid or current_step >= max_retries:
        logger.info(f"[{state.get('task_id')}] Graph: Finishing workflow.")
        return END
        
    if next_action == "navigate":
        logger.info(f"[{state.get('task_id')}] Graph: Routing back to Navigator based on overseer feedback.")
        return "navigator"

    logger.info(f"[{state.get('task_id')}] Graph: Retrying extraction.")
    return "extractor"

# Define the Graph
workflow = StateGraph(AgentState)

workflow.add_node("preparer", preparer_node)
workflow.add_node("navigator", navigator_node)
workflow.add_node("extractor", extractor_node)
workflow.add_node("overseer", overseer_node)
workflow.add_node("cleanup", cleanup_node)

workflow.set_entry_point("preparer")
workflow.add_edge("preparer", "navigator")
workflow.add_edge("navigator", "extractor")
workflow.add_edge("extractor", "overseer")

workflow.add_conditional_edges(
    "overseer",
    should_continue,
    {
        "extractor": "extractor",
        "navigator": "navigator",
        END: "cleanup"
    }
)

workflow.add_edge("cleanup", END)

app = workflow.compile()
logger.info("LangGraph workflow compiled successfully.")
