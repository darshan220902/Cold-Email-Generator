import streamlit as st
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from langchain_community.document_loaders import WebBaseLoader
from langchain_groq import ChatGroq
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import chromadb
import pandas as pd
import uuid

def scrap(url):
    loader = WebBaseLoader(url)
    data = loader.load()
    return data

# Function to process data and generate links
def fetch_from_data(data, api_key):
    llm = ChatGroq(
        temperature=0, 
        groq_api_key=api_key, 
        model_name="llama-3.1-70b-versatile"
    )

    prompt = PromptTemplate.from_template("""
        ### SCRAPED TEXT FROM WEBSITE:
        {page_data}
        ### INSTRUCTION:
        The scraped text is from the career's page of a website.
        Your job is to extract the job postings and return them in JSON format containing the following keys: `role`, `experience`, `skills` and `description`.
        Only return the valid JSON.
        ### VALID JSON (NO PREAMBLE):
        """
    )
    chain_llm = prompt | llm
    res = chain_llm.invoke(input={"page_data": data})
    try:
        json_parser = JsonOutputParser()
        res = json_parser.parse(res.content)
    except OutputParserException:
        raise OutputParserException("Context too big. Unable to parse jobs.")
    
    x = res if isinstance(res, list) else [res]
    return x[0]

# Function to generate links and create email
def generate_links(job, file, use_builtin_csv):
    if use_builtin_csv:
        df = pd.read_csv('portfolio.csv')
        client = chromadb.PersistentClient('vectostore')
        collection = client.get_or_create_collection('portfolio')
        if not collection.count():
            for _, row in df.iterrows():
                collection.add(documents=row['Techstack'],
                            metadatas={"links": row["Links"]},
                            ids=[str(uuid.uuid4())])
        links = collection.query(query_texts=job['skills'], n_results=2).get('metadatas', [])
        return links
    elif file:
        df = pd.read_csv(file)
        client = chromadb.PersistentClient('vectostore')
        collection = client.get_or_create_collection('portfolio')
        if not collection.count():
            for _, row in df.iterrows():
                collection.add(documents=row['Techstack'],
                            metadatas={"links": row["Links"]},
                            ids=[str(uuid.uuid4())])
        links = collection.query(query_texts=job['skills'], n_results=2).get('metadatas', [])
        return links
    
# Function to generate the email
def email_generate(job, links, name, company, designation, api_key):
    llm = ChatGroq(
        temperature=0, 
        groq_api_key=api_key, 
        model_name="llama-3.1-70b-versatile"
    )
    prompt_email = PromptTemplate.from_template(
        """
        ### JOB DESCRIPTION:
        {job_description}

        ### INSTRUCTION:
        
        You are {writer_name}, a {writer_designation} at {company_name}. {company_name} is a leading AI & Software Consulting company specializing in the seamless integration of business processes through advanced automated tools.
        
        Your task is to draft a concise, personalized cold email to the client based on the job description provided. The email should:

        1. Clearly highlight how {company_name} can address the client's needs as described in the job description.
        2. Emphasize the relevant skills and qualifications required for the job.
        3. Incorporate the most pertinent links from {company_name}'s portfolio to showcase our capabilities and experience related to the job requirements.

        Ensure that:
        - The email is directly tailored to the job description.
        - The email is brief and to the point, avoiding any unnecessary details or preamble.
        - The relevant skills must be mentioned in paragraph or sentence form only.
        - The portfolio links should be presented as bullet points in a separate list format, like below:

          **Portfolio:**
            - [Link 1]
            - [Link 2]
            - [Link 3]
          
        - Ensure there is exactly **one line space** after "Best regards,"

        ### EMAIL (NO PREAMBLE):
        Dear Hiring Manager,

        [Insert concise email content here]

        We have a proven track record of delivering impactful data science solutions and are confident in our ability to bring value to your organization. Here are some examples from our portfolio that showcase our relevant expertise:

        Portfolio:
        {link_list}

        We would be delighted to discuss how our expertise can help you achieve your goals.

        Thank you for considering our proposal. Please let me know if you need any additional information.
        
        Best regards,

        [One line space here]

        {writer_name}
        """
    )
    chain_email = prompt_email | llm
    mail = chain_email.invoke({"job_description": str(job), "link_list": links, "writer_name": name, "company_name": company, "writer_designation": designation})
    return mail.content

# Streamlit UI
def main():
    st.set_page_config(page_title="Email Generator", page_icon="📧")

    st.title("📧 Cold Email Generator")


    # Collect all inputs
    st.info("ℹ️ Please upload a valid CSV file with two columns: 'Techstack' and 'Links'. The CSV should contain your portfolio information.")

    file = st.file_uploader("📁 Upload CSV File of Portfolio", type=['csv'])
    use_builtin_csv = st.checkbox("Use built-in CSV data instead of uploading a file")
    url = st.text_input("🌐 Enter Job URL:", placeholder="https://example.com/careers")
    api_key = st.text_input("🔑 Enter your GROQ API Key:", type="password", placeholder="Your GROQ API Key")
    name = st.text_input("👤 Your Name", placeholder="John Doe")
    company = st.text_input("🏢 Your Company Name", placeholder="Tech Innovators Inc.")
    designation = st.text_input("💼 Your Designation", placeholder="AI Specialist")

    if st.button("Generate Email ✉️"):
        if url and api_key and name and company and designation:
            with st.spinner("Scraping and generating the email... ⏳"):
                data = scrap(url)
                job = fetch_from_data(data, api_key)
                links = generate_links(job, file, use_builtin_csv)
                email = email_generate(job, links, name, company, designation, api_key)
                st.success("✅ Email Generated Successfully!")
                st.write(email)
        else:
            st.warning("⚠️ Please fill in all fields to generate the email.")

if __name__ == "__main__":
    main()
