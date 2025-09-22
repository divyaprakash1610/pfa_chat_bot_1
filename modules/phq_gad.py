# modules/phq_gad.py

PHQ9_QUESTIONS = [
    "Over the last 2 weeks, how often have you had little interest or pleasure in doing things?",
    "Feeling down, depressed, or hopeless?",
    "Trouble falling or staying asleep, or sleeping too much?",
    "Feeling tired or having little energy?",
    "Poor appetite or overeating?",
    "Feeling bad about yourself — or that you are a failure?",
    "Trouble concentrating on things, like reading or watching TV?",
    "Moving or speaking so slowly that others notice? Or the opposite — being fidgety/restless?",
    "Thoughts that you would be better off dead or of hurting yourself?"
]

GAD7_QUESTIONS = [
    "Feeling nervous, anxious, or on edge?",
    "Not being able to stop or control worrying?",
    "Worrying too much about different things?",
    "Trouble relaxing?",
    "Being so restless that it's hard to sit still?",
    "Becoming easily annoyed or irritable?",
    "Feeling afraid as if something awful might happen?"
]

OPTIONS = [
    ("😀 Not at all", 0),
    ("😐 Several days", 1),
    ("😔 More than half the days", 2),
    ("😢 Nearly every day", 3)
]
