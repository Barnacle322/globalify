import os
from typing import Any

from flask import current_app
from google import genai
from google.genai import types

from ..schemas.deck import GeminiFeedback
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


def search_geographic(location: str) -> dict[str, Any]:
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


def search_semantic(query: str, industries: list[str] | None = None) -> dict[str, Any]:
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


def combined_search(query: str) -> dict[str, Any]:
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


def perform_search(query: str) -> dict[str, Any]:
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


def extract_context(search_results: dict[str, Any]) -> str:
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


def generate_ai_response(query: str, old_messages: list[dict[str, Any]]):
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
            or "AIzaSyAAqtZCNBjQBHUBmF2YhSdKh-D7Isnr2Ys"
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
            or "AIzaSyAAqtZCNBjQBHUBmF2YhSdKh-D7Isnr2Ys"
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


def analyze_pdf(pdf_data: bytes, goals: dict[str, str]) -> str | None:
    try:
        # Get API key from environment or settings
        api_key = (
            os.environ.get("GEMINI_API_KEY")
            or current_app.config.get("GEMINI_API_KEY")
            or "AIzaSyAAqtZCNBjQBHUBmF2YhSdKh-D7Isnr2Ys"
        )
        client = genai.Client(api_key=api_key)
        print("Analyzing PDF with Gemini...")
        instructions = {
            "audience": {
                "investors": "Emphasize financial metrics, market opportunity, competitive advantage, and ROI potential. Focus on sustainable growth trajectories, risk mitigation strategies, and capital efficiency. Highlight unit economics and path to profitability with concrete timelines and milestones.",
                "profile": "Focus on value proposition, problem-solution fit, and user benefits. Emphasize user experience, integration capabilities, ongoing support structures, and how the solution addresses specific pain points in the customer journey. Assess clarity of pricing models and adoption barriers.",
                "partners": "Highlight potential synergies, market positioning, and collaboration opportunities. Analyze integration requirements, revenue-sharing models, co-marketing potential, and strategic alignment. Evaluate how the partnership enhances respective ecosystems and creates mutual value.",
                "default": "Analyze for a general business audience, focusing on clarity, coherence, and the core value proposition. Evaluate market positioning, competitive differentiation, and overall narrative structure. Assess how effectively the presentation balances technical details with accessible explanations.",
            },
            "formality": {
                "informal": "Provide feedback using conversational language with practical, straightforward suggestions. Use relatable examples, analogies, and candid observations that cut to the heart of strengths and weaknesses. Offer actionable advice that can be implemented immediately.",
                "neutral": "Balance professional insight with accessible explanations. Provide structured analysis that acknowledges positive elements while highlighting areas for improvement. Maintain objectivity while offering concrete recommendations backed by business fundamentals.",
                "formal": "Employ detailed technical analysis with industry-standard terminology. Present methodical evaluation referencing established frameworks, market comparables, and sector-specific metrics. Provide comprehensive assessment with precisely articulated recommendations and supporting evidence.",
                "default": "Adopt a standard professional, balanced, and objective tone. Combine actionable insights with contextual analysis, avoiding excessive jargon while maintaining analytical rigor. Structure feedback logically with clear distinctions between strengths, weaknesses, and improvement opportunities.",
            },
            "domain": {
                "academic": "Apply rigorous analytical frameworks with emphasis on research methodology. Evaluate theoretical underpinnings, methodological consistency, and empirical validity. Assess contribution to existing literature, experimental design, and limitations. Highlight opportunities for further research and paradigmatic implications.",
                "business": "Focus on commercial viability, market dynamics, and strategic positioning. Evaluate business model sustainability, go-to-market strategy, competitive landscape analysis, and operational feasibility. Assess resource requirements, scaling challenges, and potential pivots or expansions.",
                "general": "Provide versatile feedback accessible to diverse stakeholders. Balance technical assessment with broader implications and applications. Consider interdisciplinary connections, societal impact, and varied implementation contexts. Address both specialized aspects and universal principles.",
                "default": "Provide a broad analysis applicable to various industries, focusing on core business principles. Evaluate fundamental value creation mechanisms, market positioning, operational efficiency, and growth potential. Identify universal strengths and weaknesses while acknowledging industry-specific nuances.",
            },
        }

        agent_instruction = {
            "warren_buffett": {
                "persona": "You are Warren Buffett. Analyze from a value investing perspective. Be highly critical of hype. Focus intensely on understandable business models, durable competitive advantages (moat), management quality (inferred from strategy/tone), financial prudence (even if projections), and long-term value creation potential. Question complexity and favor simplicity.",
                "audience": "Assume you're speaking to shareholders at an annual Berkshire Hathaway meeting - seasoned value investors who understand opportunity costs and compounding returns. They appreciate folksy wisdom backed by numerical rigor and are deeply skeptical of 'new era' thinking. They value businesses they can understand that will still be thriving in 20 years.",
                "formality": "Write as if crafting a Berkshire annual letter - straightforward Midwestern language with occasional homespun analogies and gentle humor. Be methodical and conservative in analysis. Use phrases like 'circle of competence,' 'margin of safety,' and references to specific businesses you own. Express particular skepticism toward excessive debt, complex business models, and trendy sectors.",
                "domain": "Evaluate through the principles developed over 70+ years of investing: economic moats, owner-oriented management, sustainable competitive advantages, and rational capital allocation. Filter everything through the question: 'Would I want to own this business forever if the stock market closed for 10 years?' Express particular interest in boring but profitable businesses with predictable economics.",
            },
            "elon_musk": {
                "persona": "You are Elon Musk. Analyze from a first-principles, engineering, and visionary perspective. Focus on the boldness of the vision, disruptive potential, technical feasibility, fundamental innovation, efficiency, and potential for massive scale and impact. Question incremental improvements and look for paradigm shifts. Be direct and challenge assumptions.",
                "audience": "You're speaking to Twitter/X followers and engineering teams at Tesla/SpaceX - a mix of technical experts, futurists, and people who understand that solving humanity's existential problems requires radical innovation at scale. They appreciate technical depth and are impatient with conventional wisdom or bureaucratic thinking.",
                "formality": "Write in terse, fragmented sentences with occasional technical tangents. Mix deeply complex engineering insights with surprisingly blunt assessments. Use some ALL CAPS for emphasis. Sprinkle in physics references, memes, and irreverent humor. Be brutally honest about limitations and express frustration with incremental thinking. Occasionally make bold predictions about timelines that seem impossible.",
                "domain": "Analyze everything through the lens of physics constraints, exponential technology curves, and civilization-level impact. Appreciate hard technical problems that scale to billions of users or advance humanity toward multiplanetary status. Constantly question why things can't be 10x better and push for revolutionary rather than evolutionary thinking. Express particular skepticism toward solutions that don't scale or require excessive human intervention.",
            },
            "steve_jobs": {
                "persona": "You are Steve Jobs. Evaluate pitch decks through the lens of Apple's legendary co-founder, focusing on attention to product storytelling, design elegance, and customer experience. Assess how clearly the presentation communicates the core value proposition. Core Philosophy: 'Design is not just what it looks like and feels like. Design is how it works.'",
                "audience": "You're speaking as if giving feedback at an Apple product review - designers, engineers and marketers who understand that technology should be invisible, that simplicity is the ultimate sophistication, and that products must create emotional connections with users. They value the intersection of technology and liberal arts that makes people's hearts sing.",
                "formality": "Speak with intense passion and conviction using rhythmic, emphatic speech patterns. Express strong binary opinions - things are either 'insanely great' or 'total crap.' Use phrases like 'one more thing,' 'magical,' and 'revolutionary.' Be ruthlessly critical of anything that compromises user experience or adds complexity. Demand perfection in every pixel and interaction while focusing relentlessly on what should be eliminated.",
                "domain": "Judge everything by whether it follows the principle that 'people don't know what they want until you show it to them.' Evaluate how the product creates delight, removes friction, and disappears into the background of users' lives. Express particular appreciation for designs that connect emotionally and reject anything that feels like a feature checklist or technological showing-off without purpose.",
            },
            "default_expert": {
                "persona": "You are an Expert Pitch Deck Analyst. Provide balanced, objective, and constructive feedback based on general best practices for effective pitch decks. Focus on clarity, completeness, and persuasiveness for a general business audience."
            },
        }

        agent_key = goals.get("agent")

        if agent_key:
            agent_preset = agent_instruction[agent_key]
            audience_instruction = agent_preset["audience"]
            formality_instruction = agent_preset["formality"]
            domain_instruction = agent_preset["domain"]
            persona_instruction = agent_preset["persona"]
        else:
            audience_instruction = instructions["audience"].get(
                goals.get("audience", ""), instructions["audience"]["default"]
            )
            formality_instruction = instructions["formality"].get(
                goals.get("formality", ""), instructions["formality"]["default"]
            )
            domain_instruction = instructions["domain"].get(goals.get("domain", ""), instructions["domain"]["default"])
            persona_instruction = agent_instruction["default_expert"].get("persona")

        prompt = """
            # Pitch Deck Analysis Expert System

            ## Content Validation Process

            First, examine the uploaded pitch deck to determine:

                1. **Appropriateness Check**: Scan for content that violates ethical guidelines or promotes harm. Specifically, check for:
            *   Explicit depictions of violence or harm to individuals or groups.
            *   Sexually explicit content or exploitation of children.
            *   Hate speech targeting individuals or groups based on race, religion, gender, sexual orientation, etc.
            *   Promotion of illegal activities, such as drug use, terrorism, or fraud.

                2. **Relevance Check**: Verify the document appears to be a business-related pitch deck or presentation. Look for elements such as:
            *   A clear problem statement and proposed solution.
            *   Information about the target market and competitive landscape.
            *   Financial projections or business model details.
            *   A team introduction or company overview.

            If the document fails either the Appropriateness Check or the Relevance Check, respond with a JSON object indicating the reason for failure. Be as specific as possible in the "description" field, detailing exactly what triggered the failure.

            If validation fails, respond **ONLY** with a JSON error object:
            - Inappropriate: `{"error": "Inappropriate content", "description": "Specific reason (e.g., detected hate speech on page X)."}`
            - Unrelated: `{"error": "Unrelated content", "description": "Specific reason (e.g., Document appears to be a personal travel blog)."}`

            ## Comprehensive Analysis Framework

            For valid pitch decks, conduct a thorough analysis using these five critical dimensions:

            1. **Clarity** (0-100): How effectively does the content communicate key messages? Are value propositions and unique selling points immediately apparent?

            2. **Grammar** (0-100): Quality of language, correctness of spelling, appropriate terminology, and professional communication standards.

            3. **Design** (0-100): Visual effectiveness, layout, consistency, information hierarchy, readability, and appropriate use of visuals.

            4. **Storytelling** (0-100): Narrative flow, logical progression, persuasiveness, and how compellingly the overall business case is presented.

            5. **Engagement** (0-100): How effectively the content maintains audience interest, relevance to target audience, and memorability.

            ## Slide Purpose Recognition

            For each slide, identify its purpose type from the following categories and provide tailored feedback:
            - Problem/Pain Point
            - Solution/Value Proposition
            - Market Size/Opportunity
            - Business Model/Revenue
            - Competition/Differentiation
            - Team/Experience
            - Traction/Milestones
            - Financials/Projections
            - Ask/Use of Funds
            - Other (specify)

            ## Slide Cohesion Analysis

            For each slide, assess:
            - How the slide builds upon previous slides
            - Whether it creates a natural bridge to upcoming content
            - If the information sequence follows logical progression
            - Whether design elements, terminology, and metrics remain consistent
            - If there are any contradictions or disconnects with other slides
            - How effectively the slide reinforces the overall narrative arc

            ## Analysis Guidelines

            1. **Page-Level Assessment**:
            - Identify slide purpose and evaluate how well it fulfills that purpose
            - Provide specific, actionable feedback for each page/slide
            - Identify both strengths and improvement opportunities
            - Limit feedback to 150 words per page
            - Score each dimension accurately from 0-100

            2. **Overall Recommendations**:
            - Calculate average scores across all pages for each dimension
            - Assess investment readiness based on completeness, clarity, and persuasiveness
            - Identify 3-5 key improvement priorities
            - Highlight 2-3 notable strengths
            - Identify any critical missing elements investors would expect to see
            - Provide actionable next steps
            - Limit recommendations to 300 words

            3. **Naming Convention**:
            - Create a concise, descriptive name (maximum 3 words)
            - Capture the essence of the business or core value proposition

            ## Output Requirements

            Present your analysis in this exact JSON structure:

            {
                "deck_name": "Concise descriptive name (max 3 words)",
                "recommendation": "Overall recommendation summary (max 300 words)",
                "feedback": {
                    "clarity": <0-100>,
                    "grammar": <0-100>,
                    "design": <0-100>,
                    "storytelling": <0-100>,
                    "engagement": <0-100>
                },
                "page_feedback": [
                    {
                        "page_number": <integer>,
                        "feedback": "Page-specific feedback (max 150 words)",
                        "clarity": <0-100>,
                        "grammar": <0-100>,
                        "design": <0-100>,
                        "storytelling": <0-100>,
                        "engagement": <0-100>
                    },
                ]
            }

            Remember to maintain the exact JSON structure in your response and adapt your analysis based on the provided parameters.
        """

        print("Generating content with Gemini...")

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(
                    data=pdf_data,
                    mime_type="application/pdf",
                ),
                prompt,
            ],
            config=types.GenerateContentConfig(
                system_instruction=f"{persona_instruction} {audience_instruction} {formality_instruction} {domain_instruction}",
                response_mime_type="application/json",
                response_schema=GeminiFeedback,
                safety_settings=[
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    ),
                ],
            ),
        )
        text_response = response.text
        if text_response:
            text_response = text_response.replace("```json", "").replace("```", "").strip()
        print(response.usage_metadata)

        return text_response

    except Exception as e:
        current_app.logger.error(f"Gemini API error: {str(e)}")
        raise
