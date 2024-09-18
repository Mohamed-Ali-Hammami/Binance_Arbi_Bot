from flask import render_template
from flask_socketio import SocketIO
from flask import app 

socket_io = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    socket_io.run(app, host='127.0.0.1', port=5000, debug=True)
