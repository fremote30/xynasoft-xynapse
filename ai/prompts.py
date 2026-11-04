def build_prompt(question: str, contexts: list[dict]) -> str:
    system_instructions = (
        "You are an assistant that answers questions using ONLY the provided context. "
        "If the answer cannot be found in the context, say 'I do not know based on the documents.' "
        "Do not speculate. Cite facts accurately."
    )

    context_block = "\n\n".join(
        f"[Chunk {c['chunk_index']}]\n{c['preview']}"
        for c in contexts
    )

    return f"""
SYSTEM:
{system_instructions}

CONTEXT:
{context_block}

QUESTION:
{question}

ANSWER:
""".strip()
