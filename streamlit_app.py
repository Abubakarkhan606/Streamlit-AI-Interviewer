import json
import streamlit as st
import pyttsx3
import PyPDF2
from openai import OpenAI
import speech_recognition as sr
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="Resume Chatbot", layout="centered")
st.title("Resume Insight Chatbot")
st.write("Upload your resume and answer a few questions to tailor your career path.")

# Sidebar - To upload resume
st.sidebar.header("Upload Resume")
uploaded_file = st.sidebar.file_uploader("Upload your resume (PDF)", type=["pdf"])

# State initialization
if "target_role" not in st.session_state:
    st.session_state.target_role = ""
if "goal" not in st.session_state:
    st.session_state.goal = ""
if "resume_uploaded" not in st.session_state:
    st.session_state.resume_uploaded = False

def get_resume_text():
    
    reader = PyPDF2.PdfReader(uploaded_file)
    resume_text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())

    st.session_state.resume_text = resume_text
    resume_info = extract_info(uploaded_file)

    return resume_info

def extract_info(text):
    prompt = f"""
    Extract the following from this resume text:
    - First Name
    - Last Name
    - Current Role
    - Skillset (as a list)
    
    Resume Text:
    {text}

    Calculate the following using extracted data:
    - Relevant Skills (10 missing skills relevant to Current Role)
    - Skill Gap (think of 10 skills that are most relevant to the current role, and then give a score out of 10 based on how many of those skills are present in the resume and make that score skill gap with 0 being no skill gap and 10 being a complete skill gap)
    
    Return the output in JSON format.
    """

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )

    return json.loads(response.choices[0].message.content)

def extract_from_openai():

    system_prompt = {
        "role": "system",
        "content": "You are a helpful assistant that extracts structured career information. Always respond in the format: Role: <role> or Goal: <goal>. If the input is unclear or not a job title or goal, just respond with: Invalid."
    }

    target_role = ''
    goal = ''

    # Ask for Target Role
    while not target_role:
        speak_text("What is your target role?")
        user_input = get_voice_input()
        if not user_input:
            continue  # Try again if voice not recognized

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                system_prompt,
                {"role": "user", "content": user_input}
            ]
        )
        answer = response.choices[0].message.content.strip()
        print(answer)
        speak_text(answer)

        if answer.lower().startswith("role:"):
            target_role = answer.split("Role:")[1].strip()
            st.session_state.target_role = target_role
        else:
            speak_text("That didn't seem like a valid role. Please say a specific job title.")

    # Ask for Career Goal
    while not goal:
        speak_text("What is your long-term career goal?")
        user_input = get_voice_input()
        if not user_input:
            continue

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                system_prompt,
                {"role": "user", "content": user_input}
            ]
        )
        answer = response.choices[0].message.content.strip()
        print(answer)
        speak_text(answer)

        if answer.lower().startswith("goal:"):
            goal = answer.split("Goal:")[1].strip()
            st.session_state.goal = goal
        else:
            speak_text("Please try again and describe your long-term career goal clearly.")

    speak_text("Thank you for sharing. Your information has been recorded.")
    return st.session_state.target_role, st.session_state.goal

# Voice Input
def get_voice_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎙 Speak now...")
        audio = recognizer.listen(source, timeout=15)
        st.success("Voice captured!")
        try:
            text = recognizer.recognize_google(audio)
            st.write("You said:", text)
            return text
        except sr.UnknownValueError:
            st.error("Could not understand audio.")
        except sr.RequestError:
            st.error("Speech Recognition API unavailable.")
    return None


def speak_text(text, lang='en'):
    print('enter text to speech')
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 1.0)

    engine.say(text)
    engine.runAndWait()

    print('text to speech done')

def save_to_json(resume_data, role, goal):
    data = resume_data.copy()
    data["Target Role"] = role
    data["Career Goal"] = goal

    with open("user_data.json", "w") as f:
        json.dump(data, f, indent=4)

    st.success("All data saved to user_data.json")

    with open("user_data.json", "rb") as f:
        st.download_button(
            label="⬇️ Download Extracted Info",
            data=f,
            file_name="user_data.json",
            mime="application/json"
        )

# Streamlit UI
st.title("Voice-Based Resume Info Extractor")

if uploaded_file:
    st.sidebar.success("Resume uploaded successfully!")
    st.session_state.resume_uploaded = True

    resume_text = get_resume_text()
    st.session_state.resume_text = resume_text

    if st.button("Start Interview"):
        st.subheader("Extracting Resume Data...")
        resume_data = extract_info(resume_text)
        st.json(resume_data)

        st.subheader("Voice-Based Career Questions")
        role, goal = extract_from_openai()
        if role and goal:
            st.success(f"Target Role: {role}")
            st.success(f"Career Goal: {goal}")
            save_to_json(resume_data, role, goal)
        else:
            st.error("Could not capture target role or goal.")
else:
    st.session_state.resume_uploaded = False
    st.info("Please upload a resume to begin.")
    st.stop()
