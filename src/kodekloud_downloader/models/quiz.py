import concurrent.futures
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests


@dataclass
class QuizQuestion:
    _id: Dict[str, str]
    type: int
    correctAnswers: List[str]  # noqa: N815
    code: Dict[str, str]
    question: str
    answers: List[str]
    labels: Optional[List[str]] = None
    documentationLink: Optional[str] = None  # noqa: N815
    explanation: Optional[str] = None
    topic: Optional[str] = None


@dataclass
class Quiz:
    _id: Dict[str, str]
    questions: Dict[str, str]
    name: Optional[str] = None
    topic: Optional[str] = None
    projectId: Optional[str] = None  # noqa: N815
    order: Optional[str] = None

    def fetch_questions(self) -> List[QuizQuestion]:
        quiz_questions = []

        def fetch_question(question_id):
            params = {
                "id": question_id,
            }
            url = "https://mcq-backend-main.kodekloud.com/api/questions/question"
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            if question_json := response.json():
                quiz_questions.append(QuizQuestion(**question_json))

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(fetch_question, self.questions.values())

        return quiz_questions
