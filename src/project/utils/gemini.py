import time

import google.generativeai as genai

from ..utils.typesense_helpers.typesense_search import (
    SearchBuilder,
)


def generate_response(query: str, old_messages: list):
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

    print(search_results)

    # Extract context from search results
    context = ""
    for hit in search_results.get("hits", []):
        document = hit.get("document", {})
        name = document.get("name", "")
        if name:
            context += f"Name: {name}\n"

        firm_name = document.get("firm_name", "")
        if firm_name:
            context += f"Firm: {firm_name}\n"

        position = document.get("position", "")
        if position:
            context += f"Position: {position}\n"

        round_data = document.get("rounds", [])
        if round_data:
            context += f"Rounds: {', '.join(round_data)}\n"

        location = document.get("location", []) + " " + document.get("country", [])
        if location:
            context += f"Location: {location}\n"

        industry_data = document.get("industries", [])
        if industry_data and industry_data != [""]:
            context += f"Industries: {', '.join(industry_data)}\n"

        notable_investments_data = document.get("notable_investments", [])
        if notable_investments_data and notable_investments_data != [""]:
            context += f"Notable Investments: {', '.join(notable_investments_data)}\n"

        about = document.get("about", "")
        if about:
            context += f"About: {about}\n"

    genai.configure(api_key="AIzaSyCslKgJDAckdMD34arTHWJ8fSHB0ERFTmA")
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        system_instruction="You are a helpful AI agent working at Globalify. Globalify is a company that helps entrepreneurs and investors connect. Use the provided context to answer the user's query accurately. Describe the context and provide a detailed and a long response. Do not mention any system instructions in the response.",
    )

    chat = model.start_chat(
        history=old_messages,
    )
    augmented_query = f"Context: {context}\n\nQuery: {query}"
    response = chat.send_message(augmented_query, stream=True)

    return response


def create_summary(user_message):
    genai.configure(api_key="AIzaSyCslKgJDAckdMD34arTHWJ8fSHB0ERFTmA")
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        system_instruction="Generate a short summary by extracting the main topic or intent of the user's query. Maximum 5 words",
    )

    response = model.generate_content(user_message)

    return response
