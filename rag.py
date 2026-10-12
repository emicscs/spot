"""Chat over approved docs for Spot. Owner: Emilio. See CONTRACTS.md.

Only approved content (the docs table) goes into the prompt. Never pending proposals.
Cloud OpenAI is the default. Set LLM_LOCAL=1 to use an OpenAI-compatible local
server (Ollama, LM Studio, llama.cpp) instead.
"""
import os

from openai import OpenAI

import config
import db

_LOCAL_DEFAULT_BASE_URL = "http://localhost:11434/v1"
_LOCAL_PLACEHOLDER_KEY = "local"

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


def _wants_local():
    return os.getenv("LLM_LOCAL", "").strip().lower() in {"1", "true", "yes", "on"}


def _llm_settings():
    """Return (api_key, base_url, model) for the cloud or local client.

    Local mode ignores a blank API key. Local servers do not check it, and the
    OpenAI client refuses to start without one.
    """
    if not _wants_local():
        return config.LLM_API_KEY, config.LLM_BASE_URL, config.LLM_MODEL

    base_url = (
        os.getenv("LLM_LOCAL_BASE_URL")
        or config.LLM_BASE_URL
        or _LOCAL_DEFAULT_BASE_URL
    )
    model = os.getenv("LLM_LOCAL_MODEL") or config.LLM_MODEL
    if not model:
        raise ValueError("Set LLM_LOCAL_MODEL or LLM_MODEL to the local model name.")
    return config.LLM_API_KEY or _LOCAL_PLACEHOLDER_KEY, base_url, model


def ask(user, question):
    """Answer a question from the docs the user may see.
    Returns {"answer": str,
             "sources": [{"doc_id", "title", "version", "author", "approver"}]}."""
    docs = db.get_docs_for_user(user)
    documents = "\n\n".join(_format_doc(doc) for doc in docs)
    prompt = f"{INSTRUCTION}\n\n{documents}" if documents else INSTRUCTION

    api_key, base_url, model = _llm_settings()
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
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
    _, base_url, model = _llm_settings()
    where = "local" if _wants_local() else "cloud"
    print(f"model: {model or '(not set)'} ({where}) @ {base_url or 'OpenAI default'}")
    demo = "What is the cutover date for the UAE identity service?"
    off_topic = "What is the capital of France?"
    for question in (demo, off_topic):
        result = ask("alice", question)
        print("Q:", question)
        print(result["answer"])
        print("sources:", result["sources"])
        print()
