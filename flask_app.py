from flask import Flask, render_template, request, jsonify
import asyncio
from aiohttp import web
import json
import random
import string
import websockets

app = Flask(__name__)

GRADIO_FN = 29

def random_hash():
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for i in range(9))

async def run(context):
    server = "127.0.0.1"
    params = {
        'max_new_tokens': 200,
        'do_sample': True,
        'temperature': 0.5,
        'top_p': 0.9,
        'typical_p': 1,
        'repetition_penalty': 1.05,
        'encoder_repetition_penalty': 1.0,
        'top_k': 0,
        'min_length': 0,
        'no_repeat_ngram_size': 0,
        'num_beams': 1,
        'penalty_alpha': 0,
        'length_penalty': 1,
        'early_stopping': False,
        'seed': -1,
        'add_bos_token': True,
        'truncation_length': 2048,
        'custom_stopping_strings': [],
        'ban_eos_token': False
    }
    payload = json.dumps([context, params])
    session = random_hash()

    async with websockets.connect(f"ws://{server}:7860/queue/join") as websocket:
        while content := json.loads(await websocket.recv()):
            match content["msg"]:
                case "send_hash":
                    await websocket.send(json.dumps({
                        "session_hash": session,
                        "fn_index": GRADIO_FN
                    }))
                case "estimation":
                    pass
                case "send_data":
                    await websocket.send(json.dumps({
                        "session_hash": session,
                        "fn_index": GRADIO_FN,
                        "data": [
                            payload
                        ]
                    }))
                case "process_starts":
                    pass
                case "process_generating" | "process_completed":
                    yield content["output"]["data"][0]
                    if (content["msg"] == "process_completed"):
                        break


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    user_prompt = request.form['user_prompt']
    prompt = f"{user_prompt}"

    async def get_result():
        response_text = ""
        async for response in run(prompt):
            response_text = response
        return response_text

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(get_result())
    return jsonify({'response': result})

if __name__ == '__main__':
    app.run(debug=True)
