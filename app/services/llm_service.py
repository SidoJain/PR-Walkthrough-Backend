import tiktoken
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel
from app.config import settings
from app.schemas.walkthrough import ExplanationStep

class WalkthroughOutputSchema(BaseModel):
    steps: list[ExplanationStep]

def count_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

async def generate_walkthrough_script(diff_text: str) -> list[ExplanationStep]:
    numbered_diff = "\n".join(f"{i + 1} | {line}" for i, line in enumerate(diff_text.splitlines()))
    token_count = count_tokens(numbered_diff)

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.2
    )

    parser = PydanticOutputParser(pydantic_object=WalkthroughOutputSchema)
    format_instructions = parser.get_format_instructions()

    if token_count <= 6000:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior staff engineer mentoring a junior developer through a pull request. 
            Your goal is to TEACH the architectural concepts behind these changes. 
            Focus entirely on the 'why' and the 'effect' of the modifications. 
            CRITICAL INSTRUCTIONS:
            1. Do NOT repeat, read, or dictate the raw code syntax out loud. 
            2. Explain the impact of the logic changes conceptually (e.g., "This shifts the database connection to a lazy-loading pattern to save memory" instead of "This changes db.connect() to a lambda").
            3. Group related changes into cohesive logical steps.
            4. The diff payload provided to you has explicit absolute line numbers prefixed to each line (e.g., '123 | + code'). You MUST extract and return this exact line number for your logical blocks.
            
            {format_instructions}"""),
            ("human", "Diff payload:\n{numbered_diff}")
        ])
        
        chain = prompt | llm | parser
        
        result = await chain.ainvoke({
            "numbered_diff": numbered_diff,
            "format_instructions": format_instructions
        })
        return result.steps
    else:
        # Map-Reduce logic
        file_diffs = numbered_diff.split("diff --git ")
        file_diffs = [f"diff --git {f}" for f in file_diffs if f.strip()]
        
        chunk_summaries = []
        map_prompt = ChatPromptTemplate.from_messages([
            ("system", """Summarize the key architectural logic changes for this specific file diff. 
            Focus on conceptual impact and 'why' the change was made. Do not quote raw code. 
            Note the exact line numbers (e.g., '123 | ') where the core changes occur."""),
            ("human", "{file_diff}")
        ])
        map_chain = map_prompt | llm

        for f_diff in file_diffs:
            res = await map_chain.ainvoke({"file_diff": f_diff})
            chunk_summaries.append(res.content)

        reduce_prompt = ChatPromptTemplate.from_messages([
            ("system", """Synthesize the provided file-by-file summaries into a final structured step-by-step conceptual walkthrough mapped to explicit line numbers.
            CRITICAL INSTRUCTIONS:
            1. Teach the concepts and effects of the code. Do not recite raw code syntax.
            2. Use the exact line numbers provided in the summaries.
            
            {format_instructions}"""),
            ("human", "File Summaries:\n{summaries}")
        ])
        
        reduce_chain = reduce_prompt | llm | parser
        
        combined_summaries = "\n---\n".join(chunk_summaries)
        result = await reduce_chain.ainvoke({
            "summaries": combined_summaries,
            "format_instructions": format_instructions
        })
        return result.steps