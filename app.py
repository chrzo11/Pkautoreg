from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'This bot is made by @Cybrion and currently it hosted and live for everyone'

if __name__ == '__main__':
    app.run()
