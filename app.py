import gradio as gr
import sqlite3
from huggingface_hub import InferenceClient
from gtts import gTTS
from PIL import Image
import io

conn = sqlite3.connect("aio_ai.db", check_same_thread=False)
conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
conn.execute("CREATE TABLE IF NOT EXISTS characters (id INTEGER PRIMARY KEY, username TEXT, name TEXT, prompt TEXT)")

# FIX: expliziter Provider + stabiles Free-Tier-Modell (kein StopIteration mehr)
client = InferenceClient(provider="hf-inference")

def register(u, p):
    try:
        conn.execute("INSERT INTO users VALUES (?, ?)", (u, p))
        conn.commit()
        return "✅ Registriert!"
    except:
        return "❌ Username existiert bereits"

def login(u, p):
    if conn.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p)).fetchone():
        return "✅ Angemeldet!", u
    return "❌ Falsche Daten!", ""

def get_characters(u):
    return [row[0] for row in conn.execute("SELECT name FROM characters WHERE username=?", (u,)).fetchall()] or ["Keine Charaktere"]

def create_character(u, name, prompt):
    if not name or not prompt: return "❌ Name + Prompt erforderlich!"
    conn.execute("INSERT INTO characters (username, name, prompt) VALUES (?, ?, ?)", (u, name, prompt))
    conn.commit()
    return f"✅ '{name}' erstellt!"

def chat(msg, u, char):
    if isinstance(char, list):
        char = char[0] if char else ""
    if not char or char == "Keine Charaktere":
        return "Bitte Charakter wählen"
    p = conn.execute("SELECT prompt FROM characters WHERE username=? AND name=?", (u, char)).fetchone()
    system = p[0] if p else "Du bist hilfreich."
    try:
        return client.text_generation(
            f"{system}\n\nUser: {msg}",
            model="Qwen/Qwen2.5-0.5B-Instruct",   # stabiles Free-Tier-Modell
            max_new_tokens=600,
            temperature=0.7
        )
    except Exception as e:
        return f"Fehler bei KI-Antwort: {str(e)[:200]}"

def gen_image(p):
    try:
        return Image.open(io.BytesIO(client.text_to_image(p, model="stabilityai/stable-diffusion-2-1")))
    except:
        return None

def gen_code(p):
    try:
        return client.text_generation(f"Schreibe sauberen Code: {p}", model="Qwen/Qwen2.5-0.5B-Instruct", max_new_tokens=1200)
    except:
        return "Fehler bei Code-Generierung"

def tts(text):
    try:
        gTTS(text, lang="de").save("output.mp3")
        return "output.mp3"
    except:
        return None

with gr.Blocks(title="AIO AI") as demo:
    username_state = gr.State("")

    gr.Markdown("# 🤖 AIO AI – All-in-One KI Plattform")

    with gr.Tab("🔑 Login / Registrierung"):
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Registrieren")
                ur = gr.Textbox(label="Username")
                pr = gr.Textbox(label="Passwort", type="password")
                show_pr = gr.Checkbox(label="👁 Passwort anzeigen")
                btnr = gr.Button("Registrieren", variant="primary")
                outr = gr.Textbox()
                show_pr.change(lambda x: gr.update(type="text" if x else "password"), show_pr, pr)
                btnr.click(register, [ur, pr], outr)
            with gr.Column():
                gr.Markdown("### Anmelden")
                ul = gr.Textbox(label="Username")
                pl = gr.Textbox(label="Passwort", type="password")
                show_pl = gr.Checkbox(label="👁 Passwort anzeigen")
                btnl = gr.Button("Anmelden", variant="primary")
                outl = gr.Textbox()
                show_pl.change(lambda x: gr.update(type="text" if x else "password"), show_pl, pl)
                btnl.click(login, [ul, pl], [outl, username_state])

    with gr.Tab("👤 Charaktere"):
        cn = gr.Textbox(label="Charakter-Name")
        cp = gr.Textbox(label="System-Prompt", lines=4)
        btnc = gr.Button("Erstellen", variant="primary")
        outc = gr.Textbox()
        chardd = gr.Dropdown(label="Deine Charaktere", choices=[], allow_custom_value=True)
        btnref = gr.Button("Aktualisieren")
        btnc.click(lambda u,n,p: (create_character(u,n,p), get_characters(u)), [username_state, cn, cp], [outc, chardd])
        btnref.click(get_characters, username_state, chardd)
        username_state.change(get_characters, username_state, chardd)

    with gr.Tab("💬 Chat"):
        chatdd = gr.Dropdown(label="Charakter wählen", choices=[], allow_custom_value=True)
        msg = gr.Textbox(label="Nachricht", lines=2)
        btnchat = gr.Button("Senden", variant="primary")
        outchat = gr.Textbox(label="Antwort", lines=8)
        btnchat.click(chat, [msg, username_state, chatdd], outchat)
        username_state.change(get_characters, username_state, chatdd)
        btnref.click(get_characters, username_state, chatdd)

    with gr.Tab("🖼️ Bild"):
        ip = gr.Textbox(label="Beschreibung")
        btni = gr.Button("Generieren")
        outi = gr.Image()
        btni.click(gen_image, ip, outi)

    with gr.Tab("💻 Code"):
        cprompt = gr.Textbox(label="Aufgabe")
        btncode = gr.Button("Generieren")
        outcode = gr.Code(language="python")
        btncode.click(gen_code, cprompt, outcode)

    with gr.Tab("🔊 TTS"):
        ttstext = gr.Textbox(label="Text")
        btntts = gr.Button("Vorlesen")
        outtts = gr.Audio()
        btntts.click(tts, ttstext, outtts)

demo.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft())
