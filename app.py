import gradio as gr
import sqlite3
import os
from huggingface_hub import InferenceClient
from gtts import gTTS
from PIL import Image
import io

# SQLite DB (ephemeral)
DB = "aio_ai.db"
conn = sqlite3.connect(DB, check_same_thread=False)
conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
conn.execute("CREATE TABLE IF NOT EXISTS characters (id INTEGER PRIMARY KEY, username TEXT, name TEXT, prompt TEXT)")

client = InferenceClient()

def register(username, password):
    try:
        conn.execute("INSERT INTO users VALUES (?, ?)", (username, password))
        conn.commit()
        return "✅ Registriert!"
    except:
        return "❌ Username existiert bereits"

def login(username, password):
    res = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
    return "✅ Willkommen!" if res else "❌ Falsche Daten"

def create_character(username, name, system_prompt):
    conn.execute("INSERT INTO characters (username, name, prompt) VALUES (?, ?, ?)", (username, name, system_prompt))
    conn.commit()
    return f"✅ Charakter '{name}' erstellt!"

def get_characters(username):
    return [row[1] for row in conn.execute("SELECT * FROM characters WHERE username=?", (username,)).fetchall()]

def chat(message, username, character_name):
    chars = conn.execute("SELECT prompt FROM characters WHERE username=? AND name=?", (username, character_name)).fetchone()
    prompt = chars[0] if chars else "Du bist ein hilfreicher Assistent."
    full_prompt = f"{prompt}\nUser: {message}"
    response = client.text_generation(full_prompt, model="microsoft/Phi-3-mini-4k-instruct", max_new_tokens=512)
    return response

def generate_image(prompt):
    img_bytes = client.text_to_image(prompt, model="stabilityai/stable-diffusion-2-1")
    return Image.open(io.BytesIO(img_bytes))

def generate_code(prompt):
    full = f"Schreibe sauberen Code für: {prompt}"
    return client.text_generation(full, model="microsoft/Phi-3-mini-4k-instruct", max_new_tokens=1024)

def text_to_speech(text):
    tts = gTTS(text, lang="de")
    tts.save("output.mp3")
    return "output.mp3"

# Gradio UI
with gr.Blocks(title="AIO AI") as demo:
    gr.Markdown("# 🤖 AIO AI – All-in-One KI Plattform")
    
    with gr.Tab("🔑 Login / Registrierung"):
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Registrieren")
                u1 = gr.Textbox(label="Username")
                p1 = gr.Textbox(label="Passwort", type="password")
                reg_btn = gr.Button("Registrieren")
                reg_out = gr.Textbox()
                reg_btn.click(register, [u1, p1], reg_out)
            with gr.Column():
                gr.Markdown("### Anmelden")
                u2 = gr.Textbox(label="Username")
                p2 = gr.Textbox(label="Passwort", type="password")
                login_btn = gr.Button("Anmelden")
                login_out = gr.Textbox()
                login_btn.click(login, [u2, p2], login_out)
    
    with gr.Tab("👤 Charaktere"):
        username = gr.Textbox(label="Dein Username", visible=True)
        name = gr.Textbox(label="Charakter-Name")
        prompt = gr.Textbox(label="System-Prompt", lines=5)
        create_btn = gr.Button("Charakter erstellen")
        create_out = gr.Textbox()
        create_btn.click(create_character, [username, name, prompt], create_out)
        
        char_list = gr.Dropdown(label="Deine Charaktere", choices=[])
        refresh_btn = gr.Button("Liste aktualisieren")
        refresh_btn.click(lambda u: get_characters(u), username, char_list)
    
    with gr.Tab("💬 Chat"):
        chat_char = gr.Dropdown(label="Charakter wählen")
        msg = gr.Textbox(label="Deine Nachricht")
        chat_btn = gr.Button("Senden")
        chat_output = gr.Textbox(label="Antwort")
        chat_btn.click(chat, [msg, username, chat_char], chat_output)
    
    with gr.Tab("🖼️ Bildgenerierung"):
        img_prompt = gr.Textbox(label="Beschreibe das Bild")
        img_btn = gr.Button("Bild erzeugen")
        img_output = gr.Image()
        img_btn.click(generate_image, img_prompt, img_output)
    
    with gr.Tab("💻 Code-Generator"):
        code_prompt = gr.Textbox(label="Was soll der Code tun?")
        code_btn = gr.Button("Code generieren")
        code_output = gr.Code(language="python")
        code_btn.click(generate_code, code_prompt, code_output)
    
    with gr.Tab("🔊 Text-to-Speech"):
        tts_text = gr.Textbox(label="Text zum Vorlesen")
        tts_btn = gr.Button("Sprache erzeugen")
        tts_output = gr.Audio()
        tts_btn.click(text_to_speech, tts_text, tts_output)

demo.launch(server_name="0.0.0.0", server_port=7860)
