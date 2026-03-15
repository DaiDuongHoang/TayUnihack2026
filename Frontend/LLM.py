import streamlit as st
from google.genai import Client

client = Client(api_key=st.secrets['GEMINI_API_KEY'])

system_instruction = """
You are a wardrobe assistant. Only give clothing suggestions 
and outfit ideas based on user's preferences and wardrobe. 
Do not answer unrelated questions.
"""


def get_clothing_suggestion(user_input: str) -> str:
    prompt = f'{system_instruction}\nUser: {user_input}\nAssistant:'

    response = client.models.generate_content(
        model='gemini-2.5-flash-lite', contents=prompt
    )
    return response.text


st.title('Wardrobe Assistant')

user_input = st.text_input('Ask for outfit suggestions:')

if user_input:
    suggestion = get_clothing_suggestion(user_input)
    st.write(suggestion)
