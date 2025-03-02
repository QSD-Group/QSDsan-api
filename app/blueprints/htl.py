"""
What does this file do?
It creates a blueprint for the htl endpoints our app.
It imports the htl service functions from app/services/htl_service.py.
It defines the htl_bp blueprint.
It defines two routes for the htl_bp blueprint:
One route is for the htl_calc_data function, which calculates the price and greenhouse gas emissions of HTL products.
The other route is for the htl_county_data function, which returns the HTL conversion efficiency for a given county.

What are the routes in this file?
/htl/calc
/htl/county

What does the file depend on?
app/services/htl_service.py.
- htl_convert_sludge_mass_kg_hr
- htl_calc
- htl_county

Where is this file used?
app/__init__.py
- app.register_blueprint(htl_bp, url_prefix='/api/v1') # Registers the htl_bp blueprint with the app.
"""

from flask import Blueprint, request, jsonify, make_response # Flask Version 3.0.3
from app.services.htl_service import htl_calc, htl_county, htl_convert_sludge_mass_kg_hr as htl_convert_kg

htl_bp = Blueprint('htl_bp', __name__)

@htl_bp.route('/htl/calc', methods=['GET'])
def htl_calc_data():
    """
    Takes in a sludge mass in a specified unit and returns the (i) mass of the sludge in kg/hr, (ii) price of the HTL product in $/gallon, (iii) greenhouse gas emissions in lb CO2e/gallon.
    
    URL Format - GET /htl/calc?sludge=sludge&unit=unit
    ---
    tags:
      - HTL
    parameters:
      - name: sludge
        in: query
        type: number
        format: float
        required: true
        description: The mass of the sludge
        example: 100.0
      - name: unit
        in: query
        type: string
        required: false
        description: The unit of the sludge mass, default is kg/hr
        example: 'kghr, tons, tonnes, mgd, m3d'
    responses:
      200:
        description: A successful response
        content:
          application/json:
            schema:
              type: object
              properties:
                sludge:
                  type: float
                  example: 100.0
                price:
                  type: float
                  example: 0.0
                gwp:
                  type: float
                  example: 0.0
      400:
        description: Bad request
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: 'Sludge not provided'
      422:
        description: Unprocessable entity
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: 'Invalid unit'
      500:
        description: Unexpected error
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: 'Unexpected error'
    """
    
    sludge = request.args.get('sludge', None)
    
    if sludge is None:
        return make_response(
            jsonify({"error": "Sludge not provided"}), 400 # Bad request, no sludge
        )
    
    try:
        sludge = float(sludge)
    except ValueError:
        return make_response(
            jsonify({"error": "Sludge should be a number"}), 400 # Bad request, non-float sludge
        )
    
    unit = request.args.get('unit', 'kghr')
    
    if unit not in ['kghr', 'tons', 'tonnes', 'mgd', 'm3d']:
        return make_response(
            jsonify({"error": "Invalid unit"}), 422 # Bad request, invalid unit, unprocessable entity
        )
    
    sludge = htl_convert_kg(sludge, unit) # Convert sludge to kg/hr
        
    try:
        result = htl_calc(sludge)
    except TypeError as e:
        return make_response(
            jsonify({"error": str(e)}), 500 # Unknown error, unexpected error
        )
        
    if result:
        price, gwp = htl_calc(sludge)
        response_data = {
            "sludge": sludge, # In kg/hr
            "price": price, # In $/gallon
            "gwp": gwp # In lb CO2e/gallon
        }
        return make_response(
            jsonify(response_data), 200 # Returns a success status code
        )
    
    return make_response(
        jsonify({"error": "Unexpected error"}), 500 # Unknown error
    )

    
@htl_bp.route('/htl/county', methods=['GET'])
def htl_county_data():
    """
    Takes in a county name and returns the HTL conversion efficiency for that county.
    
    URL Format - GET /htl/county?county_name=county_name
    ---
    tags:
      - HTL
    parameters:
      - name: county_name
        in: query
        type: string
        required: true
        description: 'The name of the county'
        example: 'Atlantic'
    responses:
      200:
        description: A successful response
        content:
          application/json:
            schema:
              type: object
              properties:
                county_name:
                  type: string
                  example: 'Atlantic'
                  description: 'Name of the county'
                sludge:
                  type: number
                  format: float
                  example: 0.0
                  description: 'Mass of the sludge in kg/hr'
                price:
                  type: number
                  format: float
                  example: 0.0
                  description: 'Price of the HTL product in $/gallon'
                gwp:
                  type: float
                  format: float
                  example: 0.0
                  description: 'Global warming potential in lb CO2e/gallon'
      400:
        description: Bad request
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: 'Bad request'
      404:
        description: Not found
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "County not found"
      500:
        description: Unexpected error
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Unexpected error"
    """
    
    county_name = request.args.get('county_name', None)
    
    if not county_name:
        return make_response(
            jsonify({"message": "County name not provided"}), 400
        )
    
    try:
        result = htl_county(county_name)
    except ValueError:
        return make_response(
            jsonify({"message": "County not found"}), 404 # Not found, county not found
        )
    except TypeError as e:
        return make_response(
            jsonify({"message": str(e)}), 400 # Bad request, non-float sludge
        )
    
    if result:
        name, sludge, price, gwp = result
        response_data = {
            "county_name": name, # County name
            "sludge": sludge, # In kg/hr
            "price": price, # In $/gallon
            "gwp": gwp # In lb CO2e/gallon
        }
        return make_response(
            jsonify(response_data), 200
        )
        
    return make_response(
        jsonify({"message": "Unexpected error"}), 500
    )
    