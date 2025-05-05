from db import DB
from llm_gemini import LLMGemini
import time
import re

def score_numeric_richness(text):
    return (
        5 * len(re.findall(r'\$\d+(?:\.\d+)?[MBK]?', text)) +  # Money values
        3 * len(re.findall(r'\d+%+', text)) +                 # Percentages
        1 * len(re.findall(r'\d+', text))                     # All other numbers
    )

def score_table_relevance(text):
    # Score based on table indicators and numeric content
    table_score = 3 if "table" in text.lower() else 0
    numeric_score = score_numeric_richness(text)
    return table_score + numeric_score

def extract_retrieval_queries(user_question, exclude_keywords=None, must_include=None):
    keywords = re.findall(r'\b[a-zA-Z0-9]+\b', user_question.lower())
    stopwords = {"the", "is", "for", "and", "as", "of", "to", "in", "on", "by", "with", "a", "an", "what"}
    keywords = [kw for kw in keywords if kw not in stopwords]
    ngrams = set()
    for n in range(1, 4):
        ngrams.update(" ".join(keywords[i:i+n]) for i in range(len(keywords)-n+1))
    ngrams.add(user_question)
    queries = list(ngrams)
    # Add must_include logic
    if must_include:
        queries = [f"{q} {must_include}" for q in queries]
    # Add exclusion logic
    if exclude_keywords:
        exclude_str = " ".join([f'NOT {kw}' for kw in exclude_keywords])
        queries = [f"{q} {exclude_str}" for q in queries]
    return queries

# Define exclude keywords
exclude_keywords = ["proposed", "estimated", "submitted"]

# Example: Replace this with your actual user query
user_question = "What is the CSS for HT and EHV , Industrial and Commercial consumers for 2025-26?"

# Generate retrieval queries
must_include = "approved"
ques = extract_retrieval_queries(user_question, exclude_keywords=exclude_keywords, must_include=must_include)

db = DB(db_name="test_db", whoosh_index_dir="test_whoosh", embedding_model="BAAI/bge-large-en-v1.5")
llm = LLMGemini()

top_k = 5

all_results = []
for q in ques:
    queries = [q]
    result_whoosh = db.query_whoosh(q)

    result = result_whoosh
    
    # First sort by table relevance
    result = sorted(result, key=lambda x: score_table_relevance(x), reverse=True)
    # Then sort by numeric richness within table content
    result = sorted(result, key=lambda x: score_numeric_richness(x), reverse=True)
    result = result[:top_k]

    # No need for post-retrieval filtering here
    all_results.extend(result)
    # time.sleep(5)

context = '\n\n'.join(all_results)

# Use a single overall question to prompt for all charges in a table
# print(context)
# overall_ques = "Give me CSS approved charge for EHV and HT customers as for year 2025-26"
output = llm.ask(context, question=user_question)
print(output, "\n------------------------------------------------\n")
