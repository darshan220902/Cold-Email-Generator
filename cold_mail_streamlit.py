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
import urllib.parse
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


def create_mailto_link(recipient_email, subject, body):
    encoded_subject = urllib.parse.quote(subject)
    encoded_body = urllib.parse.quote(body)
    mailto_link = f"mailto:{recipient_email}?subject={encoded_subject}&body={encoded_body}"
    return mailto_link

# Streamlit UI
# def main():
#     st.set_page_config(page_title="Cold Email Generator", page_icon="📧")

#     st.title("📧 Cold Email Generator")

#     # Initialize session state variables
#     if "email_content" not in st.session_state:
#         st.session_state.email_content = ""
#     if "recipient_email" not in st.session_state:
#         st.session_state.recipient_email = ""
#     if "email_subject" not in st.session_state:
#         st.session_state.email_subject = "Generated Email from Streamlit App"
#     if "email_generated" not in st.session_state:
#         st.session_state.email_generated = False

#     # Collect all inputs
#     st.info("ℹ️ Please upload a valid CSV file with two columns: 'Techstack' and 'Links'. The CSV should contain your portfolio information.")

#     file = st.file_uploader("📁 Upload CSV File of Portfolio", type=['csv'])
#     use_builtin_csv = st.checkbox("Use built-in CSV data instead of uploading a file")
#     url = st.text_input("🌐 Enter Job URL:", placeholder="https://example.com/careers")
#     api_key = st.text_input("🔑 Enter your GROQ API Key:", type="password", placeholder="Your GROQ API Key")
#     name = st.text_input("👤 Your Name", placeholder="John Doe")
#     company = st.text_input("🏢 Your Company Name", placeholder="Tech Innovators Inc.")
#     designation = st.text_input("💼 Your Designation", placeholder="AI Specialist")

#     # Generate email on button click
#     if st.button("Generate Email ✉️"):
#         # Ensure all necessary fields are filled
#         if url and api_key and name and company and designation:
#             with st.spinner("Scraping and generating the email... ⏳"):
#                 try:
#                     # Call your scraping and processing functions
#                     data = scrap(url)
#                     job = fetch_from_data(data, api_key)
#                     links = generate_links(job, file, use_builtin_csv)
#                     email = email_generate(job, links, name, company, designation, api_key)
                    
#                     # Store the generated email in session state
#                     st.session_state.email_content = email
#                     st.session_state.email_generated = True
                    
#                     st.success("✅ Email Generated Successfully!")
#                 except Exception as e:
#                     st.error(f"An error occurred: {e}")
#         else:
#             st.warning("⚠️ Please fill in all fields to generate the email.")

#     # Show the email content if generated
#     if st.session_state.email_generated:
#         st.write("### Generated Email Content:")
#         st.write(st.session_state.email_content)
        
#         # Input fields for the subject and recipient email address
#         st.session_state.email_subject = st.text_input("Enter the Subject", value=st.session_state.email_subject)
#         st.session_state.recipient_email = st.text_input("Enter the recipient's email address:", value=st.session_state.recipient_email)
        
#         # Button to open mailto link
#         if st.session_state.recipient_email:
#             if st.button("Open Email Client"):
#                 # Generate and display the mailto link
#                 mailto_link = create_mailto_link(st.session_state.recipient_email, st.session_state.email_subject, st.session_state.email_content)
#                 st.markdown(f'<a href="{mailto_link}" target="_blank">Click here to open your email client and compose your email</a>', unsafe_allow_html=True)

# if __name__ == "__main__":
#     main()




def main():
    st.set_page_config(page_title="Cold Email Generator", page_icon="📧")

    st.title("📧 Cold Email Generator")

    # Initialize session state variables for inputs
    if "email_content" not in st.session_state:
        st.session_state.email_content = ""
    if "recipient_email" not in st.session_state:
        st.session_state.recipient_email = ""
    if "email_subject" not in st.session_state:
        st.session_state.email_subject = "Generated Email from Streamlit App"
    if "email_generated" not in st.session_state:
        st.session_state.email_generated = False
    if "url" not in st.session_state:
        st.session_state.url = ""
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""
    if "name" not in st.session_state:
        st.session_state.name = ""
    if "company" not in st.session_state:
        st.session_state.company = ""
    if "designation" not in st.session_state:
        st.session_state.designation = ""

    # Input fields with default values set in session state
    st.info("ℹ️ Please upload a valid CSV file with two columns: 'Techstack' and 'Links'. The CSV should contain your portfolio information.")
    file = st.file_uploader("📁 Upload CSV File of Portfolio", type=['csv'])
    use_builtin_csv = st.checkbox("Use built-in CSV data instead of uploading a file", key='use_builtin_csv')
    st.session_state.url = st.text_input("🌐 Enter Job URL:", placeholder="https://example.com/careers", value=st.session_state.url)
    st.session_state.api_key = st.text_input("🔑 Enter your GROQ API Key:", type="password", placeholder="Your GROQ API Key", value=st.session_state.api_key)
    st.session_state.name = st.text_input("👤 Your Name", placeholder="John Doe", value=st.session_state.name)
    st.session_state.company = st.text_input("🏢 Your Company Name", placeholder="Tech Innovators Inc.", value=st.session_state.company)
    st.session_state.designation = st.text_input("💼 Your Designation", placeholder="AI Specialist", value=st.session_state.designation)

    # Generate email on button click
    if st.button("Generate Email ✉️"):
        # Ensure all necessary fields are filled
        if st.session_state.url and st.session_state.api_key and st.session_state.name and st.session_state.company and st.session_state.designation:
            with st.spinner("Scraping and generating the email... ⏳"):
                try:
                    # Call your scraping and processing functions
                    data = scrap(st.session_state.url)
                    job = fetch_from_data(data, st.session_state.api_key)
                    links = generate_links(job, file, use_builtin_csv)
                    email = email_generate(job, links, st.session_state.name, st.session_state.company, st.session_state.designation, st.session_state.api_key)
                    
                    # Store the generated email in session state
                    st.session_state.email_content = email
                    st.session_state.email_generated = True
                    
                    st.success("✅ Email Generated Successfully!")
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")
        else:
            st.warning("⚠️ Please fill out all the required fields to generate the email.")

    # Display generated email
    if st.session_state.email_generated:
        st.write("Generated Email:")
        st.write(st.session_state.email_content)
        
        # Email-related inputs
        st.session_state.recipient_email = st.text_input("Enter recipient's email address", value=st.session_state.recipient_email)
        st.session_state.email_subject = st.text_input("Email subject", value=st.session_state.email_subject)

        # Generate mailto link and button
        mailto_link = create_mailto_link(st.session_state.recipient_email, st.session_state.email_subject, st.session_state.email_content)
        st.markdown(f'<a href="{mailto_link}" target="_blank"><button>Open in Email Client 📧</button></a>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
