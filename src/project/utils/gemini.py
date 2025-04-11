import google.generativeai as genai
from google.generativeai.types.content_types import BlobDict, FunctionDeclaration, Tool

from ..schemas.deck import DeckAnalysisResponse
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

        If validation fails, respond **ONLY** with a JSON error object:
        - Inappropriate: `{{"error": "Inappropriate content", "description": "Specific reason (e.g., detected hate speech on page X)."}}`
        - Unrelated: `{{"error": "Unrelated content", "description": "Specific reason (e.g., Document appears to be a personal travel blog)."}}`


        ## Customization Parameters

        *   **Persona:** Defines the persona/mindset for analysis. Use this instruction: `{persona_instruction}`
        *   **Audience:** Defines the target audience perspective. Use this instruction: `{audience_instruction}`
        *   **Formality:** Defines the required tone and style. Use this instruction: `{formality_instruction}`
        *   **Domain:** Defines the industry focus. Use this instruction: `{domain_instruction}`

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

        * Overall recommendations for improvement (maximum 300 words). Focus on the key areas that need the most attention.
        * An overall score for the following categories (1-100): clarity, grammar, design, storytelling, engagement.
        * Feedback for each page of the pitch deck. Provide the page number and a short feedback (maximum 200 words) for each page.
        * Provide short informative name for pitchdeck (maximum 3 words).

        The audience for this pitch deck is: {goals['audience']}.
        The formality of the deck is: {goals['formality']}.
        The domain of the pitch deck is: {goals['domain']}.

        Output in JSON format:

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
    """

    contents = [
        BlobDict(
            mime_type="application/pdf",
            data=pdf_data,
        ),
        prompt,
    ]

    print("Generating content with Gemini...")

    response = model.generate_content(contents=contents)
    text_response = response.text
    if text_response:
        text_response = text_response.replace("```json", "").replace("```", "").strip()
    print(response.usage_metadata)

    return text_response
