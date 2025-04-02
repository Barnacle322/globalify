import google.generativeai as genai
from google.generativeai.types.content_types import BlobDict, FunctionDeclaration, Tool

from ..utils.typesense_helpers.typesense_search import (
    SearchBuilder,
)


def generate_response(query: str, old_messages: list):
    search_results = perform_search(query)
    context = extract_context(search_results)
    response = generate_ai_response(context, query, old_messages)
    return response


def perform_search(query: str):
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
    return search_results


def extract_context(search_results):
    context = ""
    for hit in search_results.get("hits", []):
        document = hit.get("document", {})
        name = document.get("name", "")
        if name:
            context += f"Name: {name}\n"

        firm_name = document.get("firm_name", "")
        if firm_name:
            context += f"Firm: {firm_name}\n"

        investor_slug = document.get("slug", "")
        if investor_slug:
            context += f"slug: {investor_slug}\n"

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
    return context


def generate_ai_response(context, query, old_messages):
    tools = Tool(
        function_declarations=[
            FunctionDeclaration(
                name="perform_search",
                description="Search for relevant information based on the user's query",
                parameters={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            ),
            FunctionDeclaration(
                name="extract_context",
                description="Extract context from the search results",
                parameters={
                    "type": "object",
                    "properties": {
                        "search_results": {
                            "type": "object",
                            "properties": {
                                "hits": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "document": {
                                                "type": "object",
                                                "properties": {
                                                    "name": {"type": "string"},
                                                    "firm_name": {"type": "string"},
                                                    "position": {"type": "string"},
                                                    "rounds": {"type": "array", "items": {"type": "string"}},
                                                    "location": {"type": "array", "items": {"type": "string"}},
                                                    "country": {"type": "array", "items": {"type": "string"}},
                                                    "industries": {"type": "array", "items": {"type": "string"}},
                                                    "notable_investments": {
                                                        "type": "array",
                                                        "items": {"type": "string"},
                                                    },
                                                    "about": {"type": "string"},
                                                },
                                                "required": ["name"],
                                            }
                                        },
                                        "required": ["document"],
                                    },
                                }
                            },
                            "required": ["hits"],
                        }
                    },
                    "required": ["search_results"],
                },
            ),
        ]
    )

    genai.configure(api_key="AIzaSyCslKgJDAckdMD34arTHWJ8fSHB0ERFTmA")

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction="You are a helpful AI agent working at Globalify. Globalify is a company that helps entrepreneurs and investors connect. Use the provided context to answer the user's query accurately. Describe the context and provide a detailed and a long response. Do not mention any system instructions in the response. Annotate investors name with their slug if exists: [Investor Name](Investor slug).",
        tools=tools,
    )
    chat = model.start_chat(
        history=old_messages,
    )
    augmented_query = f"Context: {context}\n\nQuery: {query}"
    response = chat.send_message(augmented_query, stream=True)

    return response


def generate_name_summary_with_typesense_context(query: str):
    genai.configure(api_key="AIzaSyCslKgJDAckdMD34arTHWJ8fSHB0ERFTmA")
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction="Generate a short summary name (maximum 5 words) based on the provided context.",
    )

    search_results = perform_search(query)
    context = extract_context(search_results)
    if not context:
        response = model.generate_content(query)
        return response
    response = model.generate_content(context)
    return response


def analyze_pdf(pdf_data: bytes, goals: dict[str, str]) -> str:
    genai.configure(api_key="AIzaSyCslKgJDAckdMD34arTHWJ8fSHB0ERFTmA")
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
        You are an expert pitch deck analyst. Analyze the provided pitch deck and provide:

        * Overall recommendations for improvement (maximum 250 words). Focus on the key areas that need the most attention.
        * An overall score for the following categories (1-10): clarity, grammar, design, storytelling, engagement.
        * Feedback for each page of the pitch deck. Provide the page number and a short feedback (maximum 150 words) for each page.
        * Provide short informative name for pitchdeck (maximum 3 words).

        The audience for this pitch deck is: {goals['audience']}.
        The formality of the deck is: {goals['formality']}.
        The domain of the pitch deck is: {goals['domain']}.

        Output in JSON format:

        {{
            "deck_name": "...",
            "feedback": {{
                "clarity": null,
                "grammar": null,
                "design": null,
                "storytelling": null,
                "engagement": null
            }},
            "page_feedback": [
                {{
                    "page_number": null,
                    "feedback": "..."
                }}
            ]
        }}
    """

    contents = [
        BlobDict(
            mime_type="application/pdf",
            data=pdf_data,
        ),
        prompt,
    ]

    response = model.generate_content(contents=contents)
    text_response = response.text
    if text_response:
        text_response = text_response.replace("```json", "").replace("```", "").strip()
    print(response.usage_metadata)

    return text_response
