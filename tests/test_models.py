from unittest.mock import patch

from kodekloud_downloader.models.quiz import Quiz


def test_quiz_fetch_questions_preserves_order():
    quiz = Quiz(
        _id={"$oid": "123"},
        questions={"0": "q1", "1": "q2", "2": "q3", "3": "q4", "4": "q5"},
        name="Test Quiz",
    )

    fake_questions = {
        "q1": {
            "_id": {"$oid": "q1"},
            "type": 1,
            "correctAnswers": ["A"],
            "code": {},
            "question": "Question 1",
            "answers": ["A", "B"],
        },
        "q2": {
            "_id": {"$oid": "q2"},
            "type": 1,
            "correctAnswers": ["B"],
            "code": {},
            "question": "Question 2",
            "answers": ["A", "B"],
        },
        "q3": {
            "_id": {"$oid": "q3"},
            "type": 1,
            "correctAnswers": ["A"],
            "code": {},
            "question": "Question 3",
            "answers": ["A", "B"],
        },
        "q4": {
            "_id": {"$oid": "q4"},
            "type": 1,
            "correctAnswers": ["B"],
            "code": {},
            "question": "Question 4",
            "answers": ["A", "B"],
        },
        "q5": {
            "_id": {"$oid": "q5"},
            "type": 1,
            "correctAnswers": ["A"],
            "code": {},
            "question": "Question 5",
            "answers": ["A", "B"],
        },
    }

    def fake_get(url, params, timeout):
        class MockResp:
            def raise_for_status(self):
                pass

            def json(self):
                qid = params.get("id")
                return fake_questions[qid]

        return MockResp()

    with patch("requests.get", side_effect=fake_get):
        questions = quiz.fetch_questions()
        assert len(questions) == 5
        assert [q.question for q in questions] == [
            "Question 1",
            "Question 2",
            "Question 3",
            "Question 4",
            "Question 5",
        ]
