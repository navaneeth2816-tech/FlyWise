from flask import Blueprint, request, jsonify
from services.recommendation_service import score_and_rank_itineraries, compare_itineraries

recommendation_bp = Blueprint('recommendations', __name__, url_prefix='/api/v1/recommendations')

@recommendation_bp.route('', methods=['POST'])
def rank():
    data = request.get_json() or {}
    itineraries = data.get('itineraries', [])
    user_preferences = data.get('preferences', {})
    scored = score_and_rank_itineraries(itineraries, user_preferences)
    return jsonify({"status": "success", "ranked_itineraries": scored})

@recommendation_bp.route('/compare', methods=['POST'])
def compare():
    data = request.get_json() or {}
    itineraries = data.get('itineraries', [])
    if not itineraries:
        return jsonify({"status": "error", "message": "At least one itinerary is required for comparison."}), 400
    comp = compare_itineraries(itineraries)
    return jsonify({"status": "success", "comparison": comp})

@recommendation_bp.route('/explain', methods=['POST'])
def explain():
    data = request.get_json() or {}
    itinerary = data.get('itinerary', {})
    user_preferences = data.get('preferences', {})
    scored = score_and_rank_itineraries([itinerary], user_preferences)
    item = scored[0] if scored else {}
    return jsonify({
        "status": "success",
        "itinerary_id": item.get('itinerary_id'),
        "recommendation_score": item.get('recommendation_score'),
        "score_breakdown": item.get('score_breakdown'),
        "explanations": item.get('explanations', [])
    })
