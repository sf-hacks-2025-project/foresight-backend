import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Pinecone client
api_key = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=api_key)
    
def init_pinecone(index_name="sfhacks-vectors", dimension=1536):
    """
    Initialize a Pinecone index with the given name and dimension.
    Default dimension is 1536 which matches OpenAI's text-embedding-ada-002 model.
    """
    # Check if index already exists
    try:
        if index_name not in pc.list_indexes().names():
            # Create a new index
            # Use gcp-starter for free tier
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="gcp", region="us-central1")
            )
            print(f"Created new Pinecone index: {index_name}")
        
        # Get the index
        return pc.Index(index_name)
    except Exception as e:
        print(f"Error initializing Pinecone index: {e}")
        # Return None to prevent application from crashing
        return None

def upsert_vectors(index, vectors, namespace="default"):
    """
    Insert or update vectors in the Pinecone index.
    
    Args:
        index: Pinecone index object
        vectors: List of tuples (id, vector, metadata)
        namespace: Namespace to store vectors in
    """
    items = [
        {"id": id, "values": vector, "metadata": metadata}
        for id, vector, metadata in vectors
    ]
    
    index.upsert(vectors=items, namespace=namespace)
    return len(items)

def query_vectors(index, query_vector, top_k=5, namespace="default", filter=None):
    """
    Query vectors from the Pinecone index.
    
    Args:
        index: Pinecone index object
        query_vector: The query embedding vector
        top_k: Number of results to return
        namespace: Namespace to query
        filter: Metadata filter to apply
    
    Returns:
        List of matching documents with their scores and metadata
    """
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        namespace=namespace,
        include_metadata=True,
        filter=filter
    )
    
    return results["matches"]
