"""Shared configuration. Fully implemented; nobody edits this file."""
import os

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH") or "spot.db"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or None  # None = OpenAI default
LLM_MODEL = os.getenv("LLM_MODEL", "")


if __name__ == "__main__":
    print("DB_PATH:", DB_PATH)
    print("LLM_API_KEY set:", bool(LLM_API_KEY))
    print("LLM_BASE_URL:", LLM_BASE_URL or "(OpenAI default)")
    print("LLM_MODEL:", LLM_MODEL or "(not set)")
