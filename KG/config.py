import os
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

def load_neo4j_graph(env_path: str = '.env') -> Neo4jGraph:
    # Load from environment
    load_dotenv(env_path, override=True)
    
    NEO4J_URI = os.getenv('NEO4J_URI')
    NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
    
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    # This Aura instance's database is named after the instance ID, not "neo4j"
    NEO4J_DATABASE = os.getenv('NEO4J_DATABASE', 'neo4j')

    graph = Neo4jGraph(
        url=NEO4J_URI,
        username=NEO4J_USERNAME,
        password=NEO4J_PASSWORD,
        database=NEO4J_DATABASE,
    )
    
    return graph, GEMINI_API_KEY, None