from flask import Flask, jsonify, request
from datetime import datetime, timedelta
from claudesync.configmanager import FileConfigManager
from claudesync.utils import validate_and_get_provider

app = Flask(__name__)
config = FileConfigManager()
config.set("active_provider", "claude.ai", local=True)

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        session_key = request.json.get('sessionKey')
        if not session_key:
            return jsonify({"status": "error", "message": "sessionKey is required"}), 400
            
        if not session_key.startswith('sk-ant'):
            return jsonify({"status": "error", "message": "Invalid sessionKey format"}), 400

        provider = "claude.ai"
        expires = datetime.now() + timedelta(days=30)
        config.set_session_key(provider, session_key, expires)
        
        return jsonify({
            "status": "success",
            "message": "Successfully authenticated",
            "data": {
                "provider": provider,
                "expires": expires.isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/api/chats', methods=['GET'])
def list_chats():
    try:
        provider = validate_and_get_provider(config)
        organization_id = config.get("active_organization_id")
        chats = provider.get_chat_conversations(organization_id)
        
        formatted_chats = []
        for chat in chats:
            project = chat.get("project", {})
            formatted_chat = {
                "uuid": chat.get("uuid"),
                "name": chat.get("name", "Unnamed"),
                "project_name": project.get("name") if project else None,
                "project_id": project.get("uuid") if project else None,
                "updated_at": chat.get("updated_at")
            }
            formatted_chats.append(formatted_chat)
            
        return jsonify({
            "status": "success",
            "data": formatted_chats
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/chats', methods=['POST'])
def create_chat():
    try:
        provider = validate_and_get_provider(config, require_project=True)
        organization_id = config.get("active_organization_id")
        project_id = config.get("active_project_id")

        new_chat = provider.create_chat(organization_id, project_uuid=project_id)
        return jsonify({
            "status": "success",
            "data": new_chat
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/chats/message', methods=['POST'])
def new_chat_message():
    try:
        message = request.json.get('message')
        project_id = request.json.get('project_id')
        if not message:
            return jsonify({"status": "error", "message": "message is required"}), 400
        if not project_id:
            return jsonify({"status": "error", "message": "project_id is required"}), 400

        provider = validate_and_get_provider(config)
        organization_id = config.get("active_organization_id")

        # Create new chat
        new_chat = provider.create_chat(organization_id, project_uuid=project_id)
        chat_id = new_chat["uuid"]
        
        # Send message
        response_stream = provider.send_message(organization_id, chat_id, message)
        full_response = ""
        for event in response_stream:
            if "completion" in event:
                full_response += event["completion"]
            elif "error" in event:
                return jsonify({"status": "error", "message": event["error"]}), 500

        return jsonify({
            "status": "success",
            "data": {
                "chat_id": chat_id,
                "message": message,
                "response": full_response
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
def send_message(chat_id):
    try:
        message = request.json.get('message')
        if not message:
            return jsonify({"status": "error", "message": "message is required"}), 400

        provider = validate_and_get_provider(config, require_project=True)
        organization_id = config.get("active_organization_id")
        
        response_stream = provider.send_message(organization_id, chat_id, message)
        full_response = ""
        for event in response_stream:
            if "completion" in event:
                full_response += event["completion"]
            elif "error" in event:
                return jsonify({"status": "error", "message": event["error"]}), 500

        return jsonify({
            "status": "success",
            "data": {
                "message": message,
                "response": full_response
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/chats/<chat_id>', methods=['GET'])
def get_chat_details(chat_id):
    try:
        provider = validate_and_get_provider(config)
        organization_id = config.get("active_organization_id")
        chat = provider.get_chat_conversation(organization_id, chat_id)
        
        formatted_chat = {
            "uuid": chat.get("uuid"),
            "name": chat.get("name", "Unnamed"),
            "messages": [{
                "uuid": msg.get("uuid"),
                "sender": msg.get("sender"),
                "text": msg.get("text"),
                "created_at": msg.get("created_at")
            } for msg in chat.get("chat_messages", [])]
        }
        
        return jsonify({
            "status": "success",
            "data": formatted_chat
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)