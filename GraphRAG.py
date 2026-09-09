from langchain_neo4j import GraphCypherQAChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
import textwrap


# Prompt used to turn a natural-language question into a Cypher query.
CYPHER_GENERATION_TEMPLATE = """Task: Generate a Cypher query to answer the question.
Use only the node labels, relationship types and properties in the schema below.
Do not use any label, relationship type or property that is not in the schema.
Entity names use underscores instead of spaces (e.g. "Battle_of_Waterloo", not "Battle of Waterloo").
Return only the Cypher query, with no explanation or markdown fences.

Schema:
{schema}

Question: {question}
Cypher query:"""


def generate_cypher_query(
    question: str,
    graph,
    temperature: float = 0,
    verbose: bool = True,
) -> str:
    """
    Answers a natural-language question by generating and running a Cypher
    query against the graph, using Gemini as the LLM.

    Args:
        question: The natural language question.
        graph: A langchain_neo4j.Neo4jGraph instance.
        temperature: Sampling temperature for the LLM.
        verbose: Whether the chain prints the generated Cypher.

    Returns:
        The answer text, wrapped to 60 characters per line.
    """
    cypher_prompt = PromptTemplate(
        input_variables=["schema", "question"],
        template=CYPHER_GENERATION_TEMPLATE,
    )

    llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=temperature)

    cypher_chain = GraphCypherQAChain.from_llm(
        llm,
        graph=graph,
        verbose=verbose,
        cypher_prompt=cypher_prompt,
        allow_dangerous_requests=True,  # Acknowledge the risks here.
    )

    response = cypher_chain.invoke({"query": question})
    return textwrap.fill(response["result"], 60)
