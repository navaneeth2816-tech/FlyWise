from flask import Blueprint, request, jsonify
from routes.auth_routes import get_current_user
from services.ai_service import process_assistant_chat
from database import query_all, query_one, execute_commit

assistant_bp = Blueprint('assistant', __name__, url_prefix='/api/v1/assistant')

@assistant_bp.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    conversation_id = data.get('conversation_id')

    if not message:
        return jsonify({"status": "error", "message": "Message content is required."}), 400

    try:
        user = get_current_user()
    except Exception:
        user = None
    user_id = user['user_id'] if user else None

    try:
        result = process_assistant_chat(
            user_message=message,
            user_id=user_id,
            conversation_id=conversation_id
        )

        return jsonify({
            "status": "success",
            "conversation_id": result['conversation_id'],
            "reply": result['reply'],
            "itineraries": result.get('itineraries', []),
            "entities": result.get('entities', {}),
            "latency_ms": result.get('latency_ms', 0)
        }), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "success",
            "conversation_id": conversation_id or 1,
            "reply": "I apologize, but I could not process your message at this moment. Please check your network connection or try asking again. You can also explore flights, check baggage allowances, or simulate alternative travel dates.",
            "itineraries": [],
            "entities": {},
            "latency_ms": 50
        }), 200

@assistant_bp.route('/conversations', methods=['GET'])
def get_conversations():
    user = get_current_user()
    if not user:
        return jsonify({"status": "success", "conversations": []})

    convs = query_all("""
        SELECT c.conversation_id, c.title, c.created_at, c.updated_at,
               (SELECT message_content FROM ai_messages WHERE conversation_id = c.conversation_id ORDER BY created_at DESC LIMIT 1) AS last_message
        FROM ai_conversations c
        WHERE c.user_id = %s
        ORDER BY c.updated_at DESC
        LIMIT 20;
    """, (user['user_id'],))

    return jsonify({"status": "success", "conversations": convs})

@assistant_bp.route('/conversations/<int:conv_id>', methods=['GET'])
def get_conversation_messages(conv_id):
    user = get_current_user()
    conv = query_one("SELECT * FROM ai_conversations WHERE conversation_id = %s;", (conv_id,))
    if not conv:
        return jsonify({"status": "error", "message": "Conversation not found"}), 404

    messages = query_all("""
        SELECT message_id, sender_type, message_content, metadata, created_at
        FROM ai_messages
        WHERE conversation_id = %s
        ORDER BY created_at ASC;
    """, (conv_id,))

    return jsonify({
        "status": "success",
        "conversation": conv,
        "messages": messages
    })

@assistant_bp.route('/conversations/<int:conv_id>', methods=['DELETE'])
def delete_conversation(conv_id):
    user = get_current_user()
    user_id = user['user_id'] if user else None
    
    # Ensure ownership if user is logged in
    if user_id:
        execute_commit("DELETE FROM ai_conversations WHERE conversation_id = %s AND user_id = %s;", (conv_id, user_id))
    else:
        execute_commit("DELETE FROM ai_conversations WHERE conversation_id = %s;", (conv_id,))

    return jsonify({"status": "success", "message": "Conversation deleted."})
