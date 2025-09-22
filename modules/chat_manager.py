# modules/chat_manager.py
from modules.rag import RAGRetriever
from modules.utils import call_llm_api
from modules.phq_gad import PHQ9_QUESTIONS, GAD7_QUESTIONS, OPTIONS

class ChatManager:
    def __init__(self):
        self.messages = []
        self.rag = RAGRetriever()
        self.current_test = None
        self.current_test_name = None
        self.test_index = 0
        self.test_scores = []
        self.exchange_count = 0
        self.prompted_for_test = False
        self.test_declined_count = 0
        self.chats_since_decline = 0
        self.phq9_completed = False
        self.gad7_completed = False
        self.phq9_risk = None
        self.gad7_risk = None
        self.post_phq_exchanges = 0

    def add_user_message(self, text):
        self.messages.append({"role": "user", "content": text})

    def add_bot_message(self, text):
        self.messages.append({"role": "assistant", "content": text})

    def get_messages(self):
        return self.messages

    def is_greeting(self, text):
        # More specific greeting detection - only catch actual greetings at start of conversation
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
        text_lower = text.lower().strip()
        
        # Only consider it a greeting if:
        # 1. The text starts with a greeting word, OR
        # 2. The text is just a greeting word, OR  
        # 3. The text is a greeting + basic question like "hi how are you"
        for greeting in greetings:
            if (text_lower.startswith(greeting + " ") or 
                text_lower == greeting or
                text_lower.startswith(greeting + ",") or
                (greeting in text_lower and len(text_lower.split()) <= 4 and 
                 any(word in text_lower for word in ["how", "are", "you", "doing"]))):
                return True
        return False

    def should_prompt_for_test(self):
        # Don't prompt if already in test or showing buttons
        if self.current_test is not None or self.prompted_for_test:
            return False, None
            
        # First time: after 5 chats (for PHQ9) - changed from 3 to 5
        if not self.phq9_completed and self.exchange_count >= 2:
            return True, "PHQ9"
        
        # After PHQ9 decline: every 2 chats
        if self.test_declined_count > 0 and not self.phq9_completed and self.chats_since_decline >= 2:
            return True, "PHQ9"
        
        # Prompt for GAD-7 after PHQ-9 completion and 2-3 exchanges
        if self.phq9_completed and not self.gad7_completed and self.post_phq_exchanges >= 2:
            return True, "GAD7"
            
        return False, None

    def generate_reply(self, user_input):
        # Count non-greeting exchanges
        if not self.is_greeting(user_input):
            self.exchange_count += 1
            if self.test_declined_count > 0:
                self.chats_since_decline += 1
            if self.phq9_completed and not self.gad7_completed:
                self.post_phq_exchanges += 1

        # Handle greetings
        if self.is_greeting(user_input):
            reply = "🧠 Hi there! I'm here to support you. How are you feeling today?"
            self.add_bot_message(reply)
            return reply, False, "PHQ9"

        # Get context from RAG
        top_docs = self.rag.retrieve(user_input, top_k=2)
        context_text = "\n".join([doc['content'][:1000] for doc in top_docs]) if top_docs else ""

        # Get last 5 conversations (10 messages total - 5 user + 5 bot)
        recent_messages = self.get_messages()[-10:]  # Last 10 messages = 5 conversations
        chat_history = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in recent_messages])

        # Check if we should prompt for test
        should_prompt_result = self.should_prompt_for_test()
        should_prompt = False
        test_type = "PHQ9"
        
        if should_prompt_result[0]:  # If should_prompt is True
            should_prompt, test_type = should_prompt_result
            # Don't prompt if we're already in a test phase or showing buttons
            if self.current_test is not None:
                should_prompt = False

        # Prepare LLM messages
        system_prompt = """
        You are a supportive mental health companion for students.
        
        IMPORTANT INSTRUCTIONS:
        - Always respond empathetically and contextually to what the user says
        - Use the provided chat history to maintain continuity and remember previous conversations
        - Reference previous topics, concerns, or emotions the user has shared when relevant
        - If the user greets you, greet them back naturally and do not use context
        - If the user expresses negative emotions (sadness, anxiety, stress, loneliness, etc.), respond with empathy and understanding
        - Use the context from the knowledge base to provide relevant support and advice
        - Build on previous conversations - don't repeat the same advice or questions
        - Show that you remember what the user has told you before
        - Provide personalized, thoughtful responses based on the conversation history
        - Keep responses conversational and supportive, not clinical or robotic
        """

        if should_prompt and test_type == "PHQ9":
            system_prompt += "\n- After responding to the user's message empathetically, suggest taking the mental health questionnaires: 'To better understand how you're feeling and provide more personalized support, I recommend taking the PHQ-9 and GAD-7 questionnaires. These are short, standard tools used to assess mood and anxiety. Would you like to take them now?'"
        elif should_prompt and test_type == "GAD7":
            system_prompt += "\n- After responding to the user's message, suggest completing the anxiety assessment: 'Now that we've talked more about how you've been feeling, would you like to complete the GAD-7 questionnaire to assess your anxiety levels? It will help me understand the full picture and provide better support.'"

        llm_messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"Chat History:\n{chat_history}\n\nCurrent Input: {user_input}\n\nContext: {context_text}"
            }
        ]

        reply_text = call_llm_api(messages=llm_messages)
        
        # Check if we should show test buttons
        show_buttons = should_prompt and (
            "Would you like to take" in reply_text or 
            "I recommend taking" in reply_text or 
            "would you like to complete" in reply_text
        )
        
        if show_buttons:
            self.prompted_for_test = True

        reply = f"🧠 {reply_text}"
        self.add_bot_message(reply)
        return reply, show_buttons, test_type
    
    def decline_test(self, test_type="PHQ9"):
        """Handle when user declines the test"""
        self.prompted_for_test = False
        if test_type == "PHQ9":
            self.test_declined_count += 1
            self.chats_since_decline = 0
        elif test_type == "GAD7":
            # If they decline GAD-7, reset the post-PHQ counter and mark as "declined"
            self.post_phq_exchanges = 0
    
    def start_test(self, test_name="PHQ9"):
        """Start the questionnaire"""
        self.current_test = PHQ9_QUESTIONS if test_name == "PHQ9" else GAD7_QUESTIONS
        self.current_test_name = test_name
        self.test_index = 0
        self.test_scores = []
        self.prompted_for_test = False
        return self.get_next_question()

    def get_next_question(self):
        if self.current_test and self.test_index < len(self.current_test):
            return self.current_test[self.test_index]
        return None

    def record_answer(self, score):
        if not self.current_test or self.test_index >= len(self.current_test):
            return None
        try:
            self.test_scores.append(int(score))
            self.test_index += 1
            if self.test_index >= len(self.current_test):
                return self.calculate_risk()
            return self.get_next_question()
        except (ValueError, TypeError):
            return None

    def calculate_risk(self):
        total = sum(self.test_scores)
        completed_test_name = self.current_test_name
        
        if self.current_test_name == "PHQ9":
            if total < 5:
                risk = "low"
            elif total < 15:
                risk = "moderate"
            else:
                risk = "high"
            self.phq9_completed = True
            self.phq9_risk = risk
            self.post_phq_exchanges = 0  # Reset counter for GAD-7 prompt
        else:  # GAD7
            if total < 5:
                risk = "low"
            elif total < 10:
                risk = "moderate"
            else:
                risk = "high"
            self.gad7_completed = True
            self.gad7_risk = risk
        
        # Reset test state
        self.current_test = None
        self.current_test_name = None
        self.test_index = 0
        self.test_scores = []
        
        return risk, completed_test_name
    
    def calculate_overall_risk(self):
        """Calculate overall risk based on both PHQ-9 and GAD-7 results"""
        if not (self.phq9_completed and self.gad7_completed):
            return None
        
        # Risk scoring: low=1, moderate=2, high=3
        risk_scores = {"low": 1, "moderate": 2, "high": 3}
        
        phq_score = risk_scores.get(self.phq9_risk, 0)
        gad_score = risk_scores.get(self.gad7_risk, 0)
        
        # Calculate average and determine overall risk
        avg_score = (phq_score + gad_score) / 2
        
        if avg_score <= 1.5:
            return "low"
        elif avg_score <= 2.5:
            return "moderate"
        else:
            return "high"