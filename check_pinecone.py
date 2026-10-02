"""
Simple script to verify Pinecone API key validity.
"""

import os
from app.config.settings import Settings
from pinecone import Pinecone
from pinecone.errors.exceptions import UnauthorizedError


def main():
    settings = Settings()
    api_key = settings.PINECONE_API_KEY
    if not api_key:
        print("PINECONE_API_KEY is not set. Please add it to your .env file.")
        return
    try:
        pc = Pinecone(api_key=api_key)
        indexes = pc.list_indexes().names()
        print("Pinecone connection successful. Available indexes:")
        for idx in indexes:
            print(f"- {idx}")
    except UnauthorizedError:
        print("Error: Unauthorized – the provided Pinecone API key is invalid.")
        print("Please verify that the key in .env matches your Pinecone console.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
