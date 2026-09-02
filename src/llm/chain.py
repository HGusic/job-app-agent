"""LangChain chain for screening / essay questions."""

import os
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from src.llm.context import format_profile
from src.profile import load_profile

SYSTEM_PROMPT = """You help answer job application screening questions.

Rules:
- Use ONLY facts from the candidate profile. Do not invent employers, degrees, skills, or dates.
- Write in first person.
- Be concise (2-4 sentences) unless the question clearly needs a longer answer.
- If the profile lacks info to answer well, say what you can honestly and keep it brief.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            """Candidate profile:
{profile}

Job description:
{job_description}

Question:
{question}

Answer:""",
        ),
    ]
)


@lru_cache
def get_llm() -> ChatOllama:
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    return ChatOllama(model=model, base_url=base_url, temperature=0.4)


def build_chain():
    """Prompt → LLM → text. This is the basic LangChain pattern (LCEL)."""
    return PROMPT | get_llm() | StrOutputParser()


def answer_question(question: str, job_description: str = "") -> str:
    profile_text = format_profile(load_profile())
    chain = build_chain()
    return chain.invoke(
        {
            "profile": profile_text,
            "job_description": job_description or "(not provided)",
            "question": question,
        }
    )
