from app.graph.builder import prediction_graph
from app.graph.state import GraphState

def run_prediction(data: GraphState) -> GraphState:
    return prediction_graph.invoke(data)
