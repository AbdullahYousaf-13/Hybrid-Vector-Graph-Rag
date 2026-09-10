from langchain_neo4j import GraphCypherQAChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
import textwrap


# Prompt used to turn a natural-language question into a Cypher query.
# {entity_names} is filled in at runtime from Person/Event nodes in the graph.
CYPHER_GENERATION_TEMPLATE = """Task: Generate a Cypher query to answer the question.
Use only the node labels, relationship types and properties in the schema below.
Do not use any label, relationship type or property that is not in the schema.

Person.name and Event.name are short ids from the source filenames, NOT full
biographical or Wikipedia names. Match `.name` using ONLY a value from this list:
{entity_names}

Name mapping for this graph:
- "Charles-Maurice de Talleyrand-Périgord", "Talleyrand-Périgord", "Tellerand" -> "Talleyrand"
- "Napoleon Bonaparte", "Napoléon" -> "Napoleon"
- "Battle of Waterloo", "Waterloo" -> "Battle_of_Waterloo"

Do not invent slugs such as "Charles-Maurice_de_Talleyrand-Périgord".
Underscores appear only when they are already in the list above.
Return only the Cypher query, with no explanation or markdown fences.

Schema:
{schema}

Question: {question}
Cypher query:"""


def _entity_name_catalog(graph) -> str:
    """Return Person and Event names actually stored in the graph."""
    rows = graph.query(
        """
        MATCH (n)
        WHERE n:Person OR n:Event
        RETURN labels(n)[0] AS label, n.name AS name
        ORDER BY label, name
        """
    )
    if not rows:
        return '(none found — do not guess names)'
    return "\n".join(f'- {row["label"]}: "{row["name"]}"' for row in rows)


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
        partial_variables={"entity_names": _entity_name_catalog(graph)},
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
