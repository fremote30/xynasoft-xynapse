"""Cross-check generated Bible Quiz content against the request."""

from api.services.bible_quiz_generation_service import GeneratedBibleQuiz
from api.services.bible_quiz_request_identity import BibleQuizGenerationInputs


def validate_generated_bible_quiz(
    generated: GeneratedBibleQuiz,
    inputs: BibleQuizGenerationInputs,
) -> GeneratedBibleQuiz:
    if len(generated.questions) != inputs.question_count:
        raise ValueError("Generated question count mismatch")

    if generated.quiz.difficulty != inputs.difficulty:
        raise ValueError("Generated difficulty mismatch")

    if (generated.quiz.scripture or "").strip() != inputs.scripture.strip():
        raise ValueError("Generated scripture mismatch")

    return generated
