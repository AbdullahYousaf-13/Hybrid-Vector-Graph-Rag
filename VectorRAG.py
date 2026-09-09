from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_neo4j import Neo4jVector
import textwrap
from dotenv import load_dotenv
import os

load_dotenv()


def query_vector_rag(
    question: str,
    vector_index_name: str,
    vector_node_label: str,
    vector_source_property: str,
    vector_embedding_property: str,
) -> str:
    """
    Retrieves the most relevant chunks from the Neo4j vector index and asks
    Gemini to answer the question using only those chunks.
    """

    # 1. Connect to the existing vector index in Neo4j.
    vector_store = Neo4jVector.from_existing_graph(
        embedding=GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        ),
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE"),
        index_name=vector_index_name,
        node_label=vector_node_label,
        text_node_properties=[vector_source_property],
        embedding_node_property=vector_embedding_property,
    )

    # 2. Retrieve relevant chunks.
    docs = vector_store.as_retriever(search_kwargs={"k": 4}).invoke(question)
    context = "\n\n".join(d.page_content for d in docs)

    # 3. Ask Gemini using only that context.
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Answer the user's question using only the context below. "
         "If the answer isn't in the context, say you don't know.\n\n"
         "<context>\n{context}\n</context>"),
        ("human", "{input}"),
    ])
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        temperature=0,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )

    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"context": context, "input": question})
    return textwrap.fill(result, 60)
