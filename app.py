import os
from flask import Flask, request, jsonify, render_template_string, session, send_from_directory
from uuid import uuid4
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory storage for messages (for simplicity)
messages = []

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def ensure_user_id():
    if 'user_id' not in session:
        session['user_id'] = str(uuid4())

@app.route('/')
def index():
    html_content = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chat with NMS</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .chat-container {
                width: 400px;
                background: white;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }
            .chat-box {
                flex-grow: 1;
                overflow-y: auto;
                padding: 10px;
                border-bottom: 1px solid #ffffff;
            }
            .message {
                margin-bottom: 10px;
                padding: 10px;
                border-radius: 5px;
                max-width: 70%;
                clear: both;
            }
            .message.sent {
                background-color: #dcf8c6;
                float: right;
                text-align: right;
            }
            .message.received {
                background-color: #f1f1f1;
                float: left;
                text-align: left;
            }
            .message img {
                max-width: 100%;
                height: auto;
                border-radius: 5px;
            }
            .message a {
                color: #007bff;
                text-decoration: none;
            }
            .message a:hover {
                text-decoration: underline;
            }
            #message-input-container {
                display: flex;
            }
            #message-input {
                flex-grow: 1;
                padding: 10px;
                border: none;
                box-sizing: border-box;
            }
            #file-input {
                display: none;
            }
            #file-label {
                padding: 10px;
                background: #007bff;
                border-radius: 10px;
                color: rgb(255, 255, 255);
                cursor: pointer;
            }
            #file-label:hover{
                background: #0056b3;
            }
            #send-button {
                width: 60px;
                padding: 10px;
                border: none;
                border-radius: 10px;
                background: #007bff;
                color: white;
                cursor: pointer;
            }
            #send-button:hover {
                background: #0056b3;
            }
        </style>
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-box" id="chat-box">
                <!-- Messages will be displayed here -->
            </div>
            <div id="message-input-container">
                <input type="text" id="message-input" placeholder="Type your message here...">
                <input type="file" id="file-input">
                <label for="file-input" id="file-label">File Share</label>
                <button id="send-button">Send</button>
            </div>
        </div>

        <script>
            $(document).ready(function(){
                function getMessages() {
                    $.ajax({
                        url: '/get_messages',
                        method: 'GET',
                        success: function(response) {
                            $('#chat-box').empty();
                            response.messages.forEach(function(message) {
                                var messageClass = message.isSent ? 'sent' : 'received';
                                var messageContent = '';
                                if (message.type === 'text') {
                                    messageContent = '<div class="message ' + messageClass + '">' + message.text + '</div>';
                                } else if (message.type === 'image') {
                                    messageContent = '<div class="message ' + messageClass + '"><img src="' + message.url + '" alt="Image"></div>';
                                } else if (message.type === 'file') {
                                    messageContent = '<div class="message ' + messageClass + '"><a href="' + message.url + '" target="_blank">Download ' + message.filename + '</a></div>';
                                }
                                $('#chat-box').append(messageContent);
                            });
                        }
                    });
                }

                $('#send-button').click(function(){
                    var message = $('#message-input').val();
                    var file = $('#file-input')[0].files[0];

                    if (message) {
                        $.ajax({
                            url: '/send_message',
                            method: 'POST',
                            contentType: 'application/json',
                            data: JSON.stringify({ message: message }),
                            success: function(response) {
                                if (response.status === 'success') {
                                    $('#message-input').val('');
                                    getMessages();
                                }
                            }
                        });
                    } else if (file) {
                        var formData = new FormData();
                        formData.append('file', file);
                        $.ajax({
                            url: '/upload_file',
                            method: 'POST',
                            data: formData,
                            processData: false,
                            contentType: false,
                            success: function(response) {
                                if (response.status === 'success') {
                                    $('#file-input').val('');
                                    getMessages();
                                }
                            }
                        });
                    }
                });

                getMessages();
                setInterval(getMessages, 3000);  // Poll for new messages every 3 seconds
            });
        </script>
    </body>
    </html>
    '''
    return render_template_string(html_content)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    message = data.get('message')
    user_id = session['user_id']
    if message:
        messages.append({'text': message, 'user_id': user_id, 'type': 'text'})
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'})

@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        file_url = f'/uploads/{filename}'
        user_id = session['user_id']
        file_type = 'image' if file.filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'} else 'file'
        messages.append({'url': file_url, 'user_id': user_id, 'type': file_type, 'filename': filename})
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'File type not allowed'})

@app.route('/get_messages', methods=['GET'])
def get_messages():
    user_id = session['user_id']
    user_messages = [
        {
            'text': msg.get('text'),
            'url': msg.get('url'),
            'filename': msg.get('filename'),
            'type': msg['type'],
            'isSent': msg['user_id'] == user_id
        } 
        for msg in messages
    ]
    return jsonify({'messages': user_messages})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # Run the app on host 0.0.0.0 to make it accessible over the network
    app.run(debug=True, host='0.0.0.0', port=5000)
