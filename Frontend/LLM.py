import streamlit as st
from google.genai import Client


def main():
    st.title('Gemini Streamlit Chatbot')

    # Load API key from Streamlit secrets
    key = st.secrets['GEMINI_API_KEY']
    client = Client(api_key=key)

    prompt = st.text_input('Ask something:')

    if prompt:
        # Generate text using Gemini
        response = client.generate_text(model='gemini-2.5-flash-lite', prompt=prompt)
        st.write(response.text)


if __name__ == '__main__':
    main()
