from flask import Flask

app = Flask(__name__)

@app.route('/test')
def hello():
    return 'Hello'

@app.route('/health')
def health_check():
    return 'All Good', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
