from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain import hub
from langchain_community.tools import YouTubeSearchTool
from langchain_google_genai import GoogleGenerativeAI
from sentence_transformers import SentenceTransformer
from langchain_community.utilities import GoogleSearchAPIWrapper
from langchain_core.tools import Tool
#initialize database
from neo4j import GraphDatabase
from flask import Flask, render_template, request, jsonify

import os

os.environ["GOOGLE_CSE_ID"] = "Your CSE ID"
os.environ["GOOGLE_API_KEY"] = "Your Google API key"
# Initialize Flask app
app = Flask(__name__)

# Load the language model, Neo4j, and SentenceTransformer embedder
llm = None
embedder = None
driver = None
api_key = "Your Gemini API key"

def google_search(question):
        search = GoogleSearchAPIWrapper()

        tool = Tool(
            name="google_search",
            description="Search Google for recent results.",
            func=search.run,
        )

        answer=tool.run(question)
        return answer

def load_dependencies():
    global llm, embedder, driver
    # Load Neo4j
    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = "your neo4j password"
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    # Load the language model
    llm = GoogleGenerativeAI(model="models/gemini-pro", google_api_key=api_key)
    
    # Load the SentenceTransformer embedder
    embedder = SentenceTransformer('sentence-transformers/bert-large-nli-mean-tokens')

# Load the dependencies when the app starts
load_dependencies()

# Define the function to process the user query
def suggest_medicines(user_query):
    global llm, embedder, driver
    
    # Generate the embedding for the user query
    user_query_embedding = embedder.encode(user_query)

    # Define a function to create a medicine node with embedding
    def create_medicine_node(tx, embedding, name):
        query = """
        CREATE (m:Medicine {
            embedding: $embedding,
            name: $name
        })
        RETURN m;
        """
        result = tx.run(query, embedding=embedding, name=name)
        return result.single()[0]

    # Define a function to find similar medicines
    def find_similar_medicines(tx):
        cypher_query = """
        MATCH (m1:Medicine {name: "temporary_medicine"})
        MATCH (m2:Medicine)
        WHERE m1 <> m2
        WITH m1, m2, gds.similarity.cosine(m1.embedding, m2.embedding) AS similarity
        WHERE similarity > 0.7
        RETURN m2, similarity
        ORDER BY similarity DESC
        LIMIT 5;
        """
        result = tx.run(cypher_query)
        return [record for record in result]

    # Define a function to delete the temporary node
    def delete_medicine(tx):
        cypher_query = """
        MATCH (n:Medicine) WHERE n.name = "temporary_medicine" DELETE n
        """
        tx.run(cypher_query)

    # Define a function to clean the response from the database
    def clean_response_from_DB(response_from_DB):
        response = ""
        i = 1
        for record in response_from_DB:
            node = record.data()['m2']
            node.pop('embedding')  
            response += f" Medicine {i} - Name of medicine: {node['name']} \n Drug: {node['Drug']} \n Description: {node['description']} \n Directions for use: {node['directions_for_use']} , the response should contain these medicines along with their one line description only.\n\n\n"
            i += 1
        print(response)
        return response


    # Create the medicine node
    with driver.session() as session:
        session.write_transaction(create_medicine_node, user_query_embedding, "temporary_medicine")

    # Find similar medicines
    with driver.session() as session:
        records = session.read_transaction(find_similar_medicines)
        response_from_DB = records if records else []

    # Delete the temporary node
    with driver.session() as session:
        session.write_transaction(delete_medicine)

    # Clean the response from the database
    cleaned_response = clean_response_from_DB(response_from_DB)
    db_empty = len(response_from_DB) == 0

    # Create a prompt template
    prompt = PromptTemplate(
        template="""You are a medicine expert. I am a patient who needs help with medicines.
        Give the best answer based on all the information you have. You did thorough research and found the following medicines that can help the patient.
             
        Medicines: {context}
        Question: {question}. 
        Use the context to answer the question to the best of your knowledge.
        """,
        input_variables=["context", "question"]
    )

    # Create a chain for the language model
    chat_chain = LLMChain(llm=llm, prompt=prompt)

    # Generate the final response
    response = chat_chain.invoke({
        "context": cleaned_response,
        "question": user_query
    })

    return response, db_empty


# Define routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    question = request.json.get('question')
    response, db_empty = suggest_medicines(question)
    return jsonify({"text": response['text'], "db_empty": db_empty})

@app.route('/search', methods=['POST'])
def search():
    question = request.json.get('question')
    response = google_search(question)
    return jsonify({"text": response})

    

if __name__ == '__main__':
    app.run(debug=True, port=5001)

# print(suggest_medicines("What are the medicines for type 1 diabetes?")  )