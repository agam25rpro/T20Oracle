from langgraph.graph import StateGraph, END
from app.graph.state import GraphState
from app.graph.nodes.stats_agent import stats_agent
from app.graph.nodes.venue_agent import venue_agent
from app.graph.nodes.player_form_agent import player_form_agent
from app.graph.nodes.boss_agent import boss_agent

def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("stats", stats_agent)
    graph.add_node("venue", venue_agent)
    graph.add_node("player_form", player_form_agent)
    graph.add_node("boss", boss_agent)

    graph.set_entry_point("stats")
    graph.add_edge("stats", "venue")

    graph.add_edge("venue", "player_form")
    graph.add_edge("player_form", "boss")
    graph.add_edge("boss", END)

    return graph.compile()

prediction_graph = build_graph()