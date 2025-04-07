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
    model = genai.GenerativeModel("gemini-2.0-flash")

    instructions = {
        "audience": {
            "investors": "Emphasize financial metrics, market opportunity, competitive advantage, and ROI potential",
            "customers": "Focus on value proposition, problem-solution fit, and user benefits",
            "partners": "Highlight potential synergies, market positioning, and collaboration opportunities",
            "default": "Analyze for a general business audience, focusing on clarity, coherence, and the core value proposition.",
        },
        "formality": {
            "informal": "Provide feedback using conversational language with practical, straightforward suggestions",
            "neutral": "Balance professional insight with accessible explanations",
            "formal": "Employ detailed technical analysis with industry-standard terminology",
            "default": "Adopt a standard professional, balanced, and objective tone.",
        },
        "domain": {
            "academic": "Apply rigorous analytical frameworks with emphasis on research methodology",
            "business": "Focus on commercial viability, market dynamics, and strategic positioning",
            "general": "Provide versatile feedback accessible to diverse stakeholders",
            "default": "Provide a broad analysis applicable to various industries, focusing on core business principles.",
        },
        "agent": {
            "standard_expert": "Provide balanced, objective, and constructive feedback based on general best practices for effective pitch decks. Focus on clarity, completeness, and persuasiveness for a general business audience.",
            "warren_buffett": "Analyze from a value investing perspective. Be highly critical of hype. Focus intensely on understandable business models, durable competitive advantages (moat), management quality (inferred from strategy/tone), financial prudence (even if projections), and long-term value creation potential. Question complexity and favor simplicity.",
            "elon_musk": "Analyze from a first-principles, engineering, and visionary perspective. Focus on the boldness of the vision, disruptive potential, technical feasibility, fundamental innovation, efficiency, and potential for massive scale and impact. Question incremental improvements and look for paradigm shifts. Be direct and challenge assumptions.",
            "steve_jobs": "Evaluate pitch decks through the lens of Apple's legendary co-founder, focusing on  attention to product storytelling, design elegance, and customer experience. Assess how clearly the presentation communicates the core value proposition. Core Philosophy: 'Design is not just what it looks like and feels like. Design is how it works.'",
            "default": "Provide balanced, objective, and constructive feedback based on general best practices for effective pitch decks. Focus on clarity, completeness, and persuasiveness for a general business audience.",
        },
    }

    audience_instruction = instructions["audience"].get(goals.get("audience", ""), instructions["audience"]["default"])
    formality_instruction = instructions["formality"].get(
        goals.get("formality", ""), instructions["formality"]["default"]
    )
    domain_instruction = instructions["domain"].get(goals.get("domain", ""), instructions["domain"]["default"])
    agent_instruction = instructions["agent"].get("steve_jobs", instructions["agent"]["default"])

    prompt = f"""
        # Pitch Deck Analysis Expert System

        You are an elite Pitch Deck Analyst with expertise in venture capital, business strategy, design, and storytelling. Your task is to analyze pitch deck content and provide detailed, actionable feedback in a specific JSON format.

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

        Examples Error Responses:

        {{
            "ER": "Unrelated content",
            "description": "The document is a recipe for chocolate cake and is not a business presentation."
        }}

        {{
            "error": "Inappropriate content",
            "description": "The pitch deck contains sexually suggestive images that violate our content policy on the page 13."
        }}


        ## Customization Parameters

        *   **Audience:** Defines the target audience perspective. Use this instruction: `{audience_instruction}`
        *   **Formality:** Defines the required tone and style. Use this instruction: `{formality_instruction}`
        *   **Domain:** Defines the industry focus. Use this instruction: `{domain_instruction}`
        *   **Persona:** Defines the persona/mindset for analysis. Use this instruction: `{agent_instruction}`

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

        ## Output Requirements

        Present your analysis in this exact JSON structure:


        {{
            "deck_name": "Concise descriptive name (max 3 words)",
            "recommendation": "Overall recommendation summary (max 300 words)",
            "investment_readiness": <0-100>,
            "feedback": {{
                "clarity": <0-100>,
                "grammar": <0-100>,
                "design": <0-100>,
                "storytelling": <0-100>,
                "engagement": <0-100>
            }},
            "page_feedback": [
                {{
                    "page_number": <integer>,
                    "feedback": "Page-specific feedback (max 150 words)",
                    "clarity": <0-100>,
                    "grammar": <0-100>,
                    "design": <0-100>,
                    "storytelling": <0-100>,
                    "engagement": <0-100>
                }},
            ]
        }}


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


        Remember to maintain the exact JSON structure in your response and adapt your analysis based on the provided parameters.
    """

    maybe = """"
    "analysis_depth": {
        "Quick Scan": "Surface-level evaluation focusing on key visual and structural elements",
        "Standard": "Balanced analysis of content and presentation aspects",
        "Deep Dive": "Comprehensive evaluation including market validation and strategic alignment",
        "default": "Perform standard level analysis"
    },
    "focus_areas": {
        "Technical": "Emphasize technical specifications and implementation details",
        "Financial": "Prioritize financial modeling and unit economics",
        "UX-Centric": "Focus on user experience and customer journey",
        "default": "Balance all aspects equally"
    }
    # Enhanced Pitch Deck Analysis Framework

    ## Next-Gen Validation System
    1.1 Content Safety Audit:
    - Advanced NSFW detection (incl. subtle stereotypes)
    - Plagiarism risk assessment
    - Cultural appropriateness scoring

    1.2 Relevance Matrix:
    ✔ Business model coherence
    ✔ Market validation signals
    ✔ Investment thesis alignment
    ✔ UX/UI maturity indicators

    ## Dynamic Analysis Parameters
    * Analysis Intensity: {analysis_depth_instruction}
    * Priority Focus: {focus_areas_instruction}
    * Time Horizon: {"Short-term viability" if goals.get("audience") == "Investors" else "Long-term sustainability"}

    ## Smart Scoring System
    3.1 Context-Weighted Metrics:
    - Clarity (25% weight): Message precision + cognitive load assessment
    - Visual IQ (20%): Design system coherence + accessibility score
    - Story Flow (30%): Narrative arc strength + emotional resonance
    - Data Integrity (15%): Fact validation + assumption transparency
    - Action Potential (10%): Clear CTAs + next step obviousness

    3.2 Benchmarking:
    - Industry-specific percentile rankings
    - Stage-adjusted expectations (seed vs growth)

    ## Intelligent Feedback Engine
    4.1 Auto-Generated Solutions:
    - Design alternatives for low-scoring slides
    - A/B test suggestions for key messages
    - Investor Q&A anticipation matrix

    4.2 Smart Recommendations:
    if any(score < 40 for key metrics):
        "Priority Red Flags: Immediate fixes required"
    elif avg(storytelling_scores) < 60:
        "Core Narrative Restructuring Needed"
    else:
        "Optimization Roadmap: Gradual improvements"

    ## Advanced Output Features
    {{
        "insight_graphs": [
            "narrative_tension_curve",
            "visual_attention_heatmap",
            "investor_engagement_prediction"
        ],
        "comparative_analysis": {{
            "industry_benchmark": "SaaS Startups 2023",
            "percentile_rank": 72.3
        }},
        "redesign_preview": "Base64-encoded sample slide concepts"
    }}

    """

    oldPrompt = f"""
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
            "recommendation": "...",
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
                    "clarity": null,
                    "grammar": null,
                    "design": null,
                    "storytelling": null,
                    "engagement": null
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
