from langchain import hub
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Neo4jVector
import textwrap
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
load_dotenv()
def query_vector_rag(
    question: str,
    vector_index_name: str,
    vector_node_label: str,
    vector_source_property: str,
    vector_embedding_property: str
) -> str:
    """
    Initializes the vector store and retrieval chain based on provided inputs,
    then queries the system with the provided question.

    Args:
        question: The question to send to the retrieval chain.
        neo4j_uri: The URI of the Neo4j database.
        neo4j_username: The username for the Neo4j database.
        neo4j_password: The password for the Neo4j database.
        vector_index_name: The name of the vector index.
        vector_node_label: The label of the nodes that are embedded.
        vector_source_property: The node property that contains the source text.
        vector_embedding_property: The node property where the embedding is stored.
    
    Returns:
        A formatted answer string (wrapped to 60 characters per line).
    """

    # Create the vector store from the existing Neo4j graph using provided inputs.
    vector_store = Neo4jVector.from_existing_graph(
        embedding=OpenAIEmbeddings(),
        url=os.getenv('NEO4J_URI'),
        username=os.getenv('NEO4J_USERNAME'),
        password=os.getenv('NEO4J_PASSWORD'),
        index_name=vector_index_name,
        node_label=vector_node_label,
        text_node_properties=[vector_source_property],
        embedding_node_property=vector_embedding_property,
    )

    # Retrieve the retrieval QA chat prompt.
    retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")

    # Create a chain to combine the retrieved documents.
    combine_docs_chain = create_stuff_documents_chain(
        ChatOpenAI(temperature=0),
        retrieval_qa_chat_prompt
    )

    # Build the retrieval chain with the vector store as retriever.
    retrieval_chain = create_retrieval_chain(
        retriever=vector_store.as_retriever(),
        combine_docs_chain=combine_docs_chain
    )

    # Invoke the retrieval chain using the input question.
    result = retrieval_chain.invoke(input={"input": question})
    return textwrap.fill(result['answer'], 60)