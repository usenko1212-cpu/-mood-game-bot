"""
Вопросы и логика анализа настроения пользователя.
"""

QUESTIONS = [
    {
        "text": "😊 Как ты себя сейчас чувствуешь?",
        "options": [
            "😴 Устал(а), хочу расслабиться",
            "😤 Злюсь или раздражён(а)",
            "😊 В хорошем настроении, бодр(а)",
            "😢 Грустно, хочется отвлечься",
            "🤩 Полон(на) энергии!"
        ]
    },
    {
        "text": "⏰ Сколько времени у тебя есть?",
        "options": [
            "⚡ 15–30 минут",
            "🕐 1–2 часа",
            "🌙 Весь вечер",
            "🏖 Весь день!"
        ]
    },
    {
        "text": "👥 С кем ты хочешь играть?",
        "options": [
            "🧍 Один(а)",
            "👫 С другом/подругой",
            "👨‍👩‍👧 С несколькими людьми",
            "🌐 С незнакомцами онлайн"
        ]
    },
    {
        "text": "🧠 Насколько ты готов(а) думать?",
        "options": [
            "🧸 Хочу просто кликать, без думанья",
            "🎯 Немного стратегии — ок",
            "🧩 Люблю хорошие головоломки",
            "♟ Хочу жёсткий вызов для мозга"
        ]
    },
    {
        "text": "🎭 Какой жанр тебе сейчас ближе?",
        "options": [
            "💥 Экшен, стрелялки",
            "🌍 Приключения, сюжет",
            "🏗 Строить, создавать",
            "🃏 Казуальные / инди",
            "👾 Что угодно, удиви меня!"
        ]
    }
]


def analyze_answers(answers: list) -> tuple[str, str]:
    """
    Анализирует ответы и возвращает (mood_key, mood_label).

    Настроения:
      relaxed   — хочет расслабиться
      energetic — полон энергии / злится (выброс)
      sad       — грустит
      social    — хочет играть с людьми
      challenge — любит сложность / вызов
      casual    — мало времени / без думанья
    """
    scores = {
        "relaxed": 0,
        "energetic": 0,
        "sad": 0,
        "social": 0,
        "challenge": 0,
        "casual": 0,
    }

    # Вопрос 1 — эмоция
    mood_map = {
        "Устал(а), хочу расслабиться":   "relaxed",
        "Злюсь или раздражён(а)":         "energetic",
        "В хорошем настроении, бодр(а)":  "energetic",
        "Грустно, хочется отвлечься":     "sad",
        "Полон(на) энергии!":             "energetic",
    }
    for key, val in mood_map.items():
        if key in answers[0]:
            scores[val] += 3

    # Вопрос 2 — время
    if "15–30" in answers[1]:
        scores["casual"] += 2
    elif "Весь день" in answers[1]:
        scores["challenge"] += 2
        scores["energetic"] += 1
    elif "Весь вечер" in answers[1]:
        scores["relaxed"] += 1
        scores["social"] += 1

    # Вопрос 3 — компания
    if "Один" in answers[2]:
        scores["relaxed"] += 1
        scores["sad"] += 1
    elif "другом" in answers[2]:
        scores["social"] += 2
    elif "несколькими" in answers[2]:
        scores["social"] += 3
    elif "незнакомцами" in answers[2]:
        scores["energetic"] += 2
        scores["social"] += 1

    # Вопрос 4 — мозговая нагрузка
    if "просто кликать" in answers[3]:
        scores["casual"] += 3
        scores["relaxed"] += 1
    elif "немного стратегии" in answers[3].lower():
        scores["casual"] += 1
        scores["relaxed"] += 1
    elif "головоломки" in answers[3]:
        scores["challenge"] += 2
    elif "жёсткий вызов" in answers[3]:
        scores["challenge"] += 3

    # Вопрос 5 — жанр
    if "Экшен" in answers[4]:
        scores["energetic"] += 2
    elif "Приключения" in answers[4]:
        scores["sad"] += 1
        scores["relaxed"] += 1
    elif "Строить" in answers[4]:
        scores["relaxed"] += 2
        scores["casual"] += 1
    elif "Казуальные" in answers[4]:
        scores["casual"] += 2
    elif "удиви" in answers[4]:
        scores["energetic"] += 1

    best_mood = max(scores, key=lambda k: scores[k])

    labels = {
        "relaxed":   "Расслабленное 😌",
        "energetic":  "Энергичное 🔥",
        "sad":        "Меланхоличное 🌧",
        "social":     "Социальное 👥",
        "challenge":  "Соревновательное 🏆",
        "casual":     "Ленивое 🛋",
    }

    return best_mood, labels[best_mood]
