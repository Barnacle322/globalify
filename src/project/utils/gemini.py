import os
from typing import Any, Dict, List, Optional

from flask import current_app
from google import genai
from google.genai import types

from ..utils.typesense_helpers.typesense_search import (
    SearchBuilder,
)


def generate_response(query: str, old_messages: list):
    """
    Generate an AI response based on the query and conversation history.

    Args:
        query: The user's query
        old_messages: Previous messages in the conversation

    Returns:
        A generator with the AI's response
    """
    print("generate response")
    try:
        response = generate_ai_response(query, old_messages)
        return response
    except Exception as e:
        current_app.logger.error(f"Error generating response: {str(e)}")
        raise


def search_geographic(location: str) -> Dict[str, Any]:
    """
    Search for investors based on geographic location.

    Args:
        location: Geographic location such as a country or city

    Returns:
        Search results filtered by geographic location
    """
    print("geographic search")
    try:
        search_builder = SearchBuilder("investors").query(location).query_by(["location", "country"])
        search_results = search_builder.search()
        return search_results
    except Exception as e:
        current_app.logger.error(f"Geographic search error: {str(e)}")
        return {"hits": []}


def search_semantic(query: str, industries: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Search for investors based on semantic meaning, industries, or interests.

    Args:
        query: Semantic search query
        industries: Optional list of specific industries to filter by

    Returns:
        Search results matching the semantic query
    """
    print("semantic search")
    try:
        search_builder = (
            SearchBuilder("investors")
            .query(query)
            .query_by(["embedding", "industries", "rounds", "notable_investments", "about"])
        )

        # Add industry filter if provided
        if industries and len(industries) > 0:
            search_builder = search_builder.filter_by("industries", industries)

        search_results = search_builder.search()
        return search_results
    except Exception as e:
        current_app.logger.error(f"Semantic search error: {str(e)}")
        return {"hits": []}


def combined_search(query: str) -> Dict[str, Any]:
    """
    Perform both geographic and semantic searches and combine results.
    This is a fallback for general queries.

    Args:
        query: The search query

    Returns:
        Combined search results
    """
    print("combined search")
    try:
        # Get geographic results
        geo_results = search_geographic(query)
        geo_hits = geo_results.get("hits", [])

        # If geographic search yields good results, prioritize those
        if len(geo_hits) > 2:
            return geo_results

        # Otherwise, try semantic search
        semantic_results = search_semantic(query)
        semantic_hits = semantic_results.get("hits", [])

        # If both have results, combine them with geographic results first
        if len(geo_hits) > 0 and len(semantic_hits) > 0:
            # Create a new result set with combined hits
            combined_hits = geo_hits + semantic_hits
            return {"hits": combined_hits, "found": len(combined_hits)}

        # If semantic has results but geo doesn't, return semantic
        if len(semantic_hits) > 0:
            return semantic_results

        # Fallback to the old search method if both specialized searches fail
        return perform_search(query)
    except Exception as e:
        current_app.logger.error(f"Combined search error: {str(e)}")
        return {"hits": []}


def perform_search(query: str) -> Dict[str, Any]:
    """
    Search for investors using Typesense based on the query. It can get any kind of query, including geographic and semantic. This should be used if other tools aren't available.
    It is a fallback for general queries.
    It can be used to search for any kind of query, including geographic and semantic.

    Args:
        query: The search query

    Returns:
        Search results
    """
    print("perform search")
    try:
        search_builder = (
            SearchBuilder("investors")
            .query(query)
            .query_by(
                [
                    "location",
                    "country",
                    "rounds",
                    "industries",
                    "embedding",
                    "notable_investments",
                    "name",
                    "firm_name",
                    "position",
                ]
            )
        )
        search_results = search_builder.search()
        return search_results
    except Exception as e:
        current_app.logger.error(f"Search error: {str(e)}")
        # Return empty results on error rather than failing
        return {"hits": []}


def extract_context(search_results: Dict[str, Any]) -> str:
    """
    Extract context from search results.

    Args:
        search_results: Results from the search

    Returns:
        Extracted context as a string
    """
    if not search_results or "hits" not in search_results or not search_results["hits"]:
        return ""

    context = ""
    for hit in search_results["hits"]:
        if "document" in hit:
            doc = hit["document"]

            # Add name and position
            if "name" in doc:
                context += f"Name: {doc['name']}\n"
            if "position" in doc:
                context += f"Position: {doc['position']}\n"
            if "firm_name" in doc:
                context += f"Firm: {doc['firm_name']}\n"

            # Add location information
            if "location" in doc and doc["location"]:
                context += f"Location: {', '.join(doc['location'])}\n"
            if "country" in doc and doc["country"]:
                context += f"Country: {', '.join(doc['country'])}\n"

            # Add investment details
            if "rounds" in doc and doc["rounds"]:
                context += f"Investment Rounds: {', '.join(doc['rounds'])}\n"
            if "industries" in doc and doc["industries"]:
                context += f"Industries: {', '.join(doc['industries'])}\n"
            if "notable_investments" in doc and doc["notable_investments"]:
                context += f"Notable Investments: {', '.join(doc['notable_investments'])}\n"

            # Add about information if available
            if "about" in doc and doc["about"]:
                context += f"About: {doc['about']}\n"

            # Add slug for linking
            if "slug" in doc:
                context += f"Slug: {doc['slug']}\n"

            context += "\n----\n"

    return context.strip()


def generate_ai_response(query: str, old_messages: List[Dict[str, Any]]):
    """
    Generate AI response using Gemini API with function calling.

    Args:
        query: The user's query
        old_messages: Previous conversation messages

    Returns:
        Generated AI response
    """

    # Define system instruction
    system_instruction = (
        "You are a helpful AI agent working at Globalify. Globalify is a company that helps entrepreneurs and "
        "Provide detailed responses about investors based on the information you find. "
        "Annotate investor names with their slug if it exists: [Investor Name](investor_slug)."
    )

    # Convert old messages to the format expected by the Gemini API
    formatted_messages = []
    if old_messages:
        for msg in old_messages:
            formatted_messages.append(
                {"role": msg.get("role", "user"), "parts": [{"text": part} for part in msg.get("parts", [])]}
            )

    # Add the current query with context
    formatted_messages.append({"role": "user", "parts": [{"text": f"Query: {query}"}]})

    try:
        # Get API key from environment or settings
        api_key = (
            os.environ.get("GEMINI_API_KEY")
            or current_app.config.get("GEMINI_API_KEY")
            or "AIzaSyCslKgJDAckdMD34arTHWJ8fSHB0ERFTmA"
        )

        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            tools=[search_geographic, search_semantic],
            system_instruction=system_instruction,
        )

        response = client.models.generate_content_stream(
            model="gemini-2.0-flash",
            contents=formatted_messages,
            config=config,
        )

        return response
    except Exception as e:
        current_app.logger.error(f"Gemini API error: {str(e)}")
        raise


def generate_name_summary_with_typesense_context(query: str):
    """
    Generate a summary name for a chat based on the query.

    Args:
        query: The user's query

    Returns:
        A summary name for the chat
    """
    try:
        # Get API key from environment or settings
        api_key = (
            os.environ.get("GEMINI_API_KEY")
            or current_app.config.get("GEMINI_API_KEY")
            or "AIzaSyCslKgJDAckdMD34arTHWJ8fSHB0ERFTmA"
        )
        client = genai.Client(api_key=api_key)

        search_results = perform_search(query)
        context = extract_context(search_results)

        if not context:
            # Simplified version that returns a string instead of a complex response object
            response = client.models.generate_content(
                model="gemini-1.5-flash",  # Fall back to 1.5 for simple generation
                contents=[
                    {"role": "user", "parts": [{"text": f"Generate a 3-5 word title for this question: {query}"}]}
                ],
                config={"temperature": 0.2, "max_output_tokens": 10},
            )
            return response.text

        # Generate with context
        response = client.models.generate_content(
            model="gemini-1.5-flash",  # Fall back to 1.5 for simple generation
            contents=[
                {
                    "role": "user",
                    "parts": [{"text": f"Context: {context}\n\nGenerate a 3-5 word title for this question: {query}"}],
                }
            ],
            config={"temperature": 0.2, "max_output_tokens": 10},
        )
        return response.text
    except Exception as e:
        current_app.logger.error(f"Error generating chat name: {str(e)}")
        # Return a simple fallback
        return "New Chat"
