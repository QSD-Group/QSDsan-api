# This is simply a trial blueprint to test some stuff out overall
# We will test both our API and the Swagger docs to see if this works

from flask import Blueprint, request, jsonify, make_response

trial_bp = Blueprint('trial_bp', __name__)

@trial_bp.route('/trial', methods=['GET'])
def trial():
    """
    A trial endpoint to test Swagger documentation.
    ---
    tags:
      - Trial
    responses:
      200:
        description: A successful response
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "This is a trial blueprint to test some stuff out overall"
    """
    return jsonify({'message': 'This is a trial blueprint to test some stuff out overall'})

