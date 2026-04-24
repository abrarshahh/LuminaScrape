import os
from typing import Literal
from langgraph.graph import StateGraph, END
from core.state import AgentState
from agents.preparer import PreparerAgent
from agents.extractor import ExtractorAgent
from agents.overseer import OverseerAgent
from core.browser import BrowserManager

# Initialize agents
preparer = PreparerAgent()
extractor = ExtractorAgent()
overseer = OverseerAgent()

async def preparer_node(state: AgentState):
    from core.browser import BrowserManager
    browser_manager = BrowserManager()
    page = await browser_manager.start()
    
    result = await preparer.run(state, page)
    state.update(result)
    return state

async def extractor_node(state: AgentState):
    from core.browser import BrowserManager
    browser_manager = BrowserManager()
    page = browser_manager.page 
    
    result = await extractor.run(state, page)
    state.update(result)
    return state

async def overseer_node(state: AgentState):
    result = await overseer.run(state)
    state.update(result)
    return state

def should_continue(state: AgentState) -> Literal["extractor", "__end__"]:
    """
    Conditional edge to decide whether to retry extraction or finish.
    """
    max_retries = int(os.getenv("MAX_EXTRACTION_RETRIES", 10))
    if state["is_valid"] or state["step_count"] >= max_retries:
        return END
    return "extractor"

# Define the Graph
workflow = StateGraph(AgentState)

workflow.add_node("preparer", preparer_node)
workflow.add_node("extractor", extractor_node)
workflow.add_node("overseer", overseer_node)

workflow.set_entry_point("preparer")
workflow.add_edge("preparer", "extractor")
workflow.add_edge("extractor", "overseer")

workflow.add_conditional_edges(
    "overseer",
    should_continue,
    {
        "extractor": "extractor",
        END: END
    }
)

app = workflow.compile()
