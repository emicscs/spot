"""Chat over approved docs for Spot. Owner: Contributor 5. See CONTRACTS.md.

Only approved content (the docs table) goes into the prompt. Never pending proposals.
"""
from openai import OpenAI

import config
import db

INSTRUCTION = (
    "Answer only from these documents. Cite title, version, author, and approver "
    "for every claim. If the answer isn't in the documents, say so: "
    "the answer is not in your documents."
)


def _format_doc(doc):
    return (
        f"Title: {doc['title']}\n"
        f"Version: {doc['version']}\n"
        f"Author: {doc['author']}\n"
        f"Approver: {doc['approver']}\n"
        f"Content:\n{doc['content']}"
    )


def ask(user, question):
    """Answer a question from the docs the user may see.
    Returns {"answer": str,
             "sources": [{"doc_id", "title", "version", "author", "approver"}]}."""
    docs = db.get_docs_for_user(user)
    documents = "\n\n".join(_format_doc(doc) for doc in docs)
    prompt = f"{INSTRUCTION}\n\n{documents}" if documents else INSTRUCTION

    client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)
    response = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ],
    )
    answer = response.choices[0].message.content or ""
    sources = [
        {
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "version": doc["version"],
            "author": doc["author"],
            "approver": doc["approver"],
        }
        for doc in docs
    ]
    return {"answer": answer, "sources": sources}


if __name__ == "__main__":
    demo = "What is the cutover date for the UAE identity service?"
    off_topic = "What is the capital of France?"
    for question in (demo, off_topic):
        result = ask("priya.raman", question)
        print("Q:", question)
        print(result["answer"])
        print("sources:", result["sources"])
        print()
