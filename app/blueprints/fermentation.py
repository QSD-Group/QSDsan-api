"""
What does the file do?
- This file contains the routes for the fermentation blueprint.
- The fermentation blueprint contains routes for the fermentation calculations.
- The fermentation calculations include the mass of the feed
- The ethanol produced in MM gallons/year
- The price of ethanol in $/gallon
- The greenhouse gas emissions in lb CO2e/gallon
- The fermentation conversion efficiency for a county

What are the routes in this file?
- /fermentation/calc
- /fermentation/county

What does the file depend on?
app/services/fermentation_service.py
- fermentation_convert_feedstock_kg_hr
- fermentation_calc
- fermentation_county

Where is this file used?
app/__init__.py
"""
from flask import Blueprint, request, jsonify, make_response
from app.services.fermentation_service import fermentation_calc, fermentation_county, fermentation_convert_feedstock_kg_hr as fermentation_kg

fermentation_bp = Blueprint('fermentation_bp', __name__)

@fermentation_bp.route('/fermentation/calc', methods=['GET'])
def fermentation_calc_data():
    """
    Takes in a mass amount in a specified unit and returns the (i) mass of the feedstock in kg/hr, (ii) ethanol produced in MM gallons/year, (iii) price of ethanol in $/gallon, (iv) greenhouse gas emissions in lb CO2e/gallon.
    
    URL Format - GET /fermentation/calc?mass=mass&unit=unit
    ---
    tags:
      - Fermentation
    parameters:
      - name: mass
          in: query
          type: number
          format: float
          required: true
          description: The mass of the feed
          example: 100.0
    - name: unit
      in: query
      type: string
      required: true
      description: The unit of the mass
      example: 'kghr, tons, tonnes'
    responses:
      200:
        description: A successful response
        content:
          application/json:
            schema:
              type: object
              properties:
                mass:
                  type: number
                  format: float
                  example: 100.0
                  description: The mass of the feedstock in kg/hr
                ethanol:
                  type: number
                  format: float
                  example: 0.0
                  description: The ethanol produced in MM gallons/year
                price:
                  type: number
                  format: float
                  example: 0.0
                  description: The price of ethanol in $/gallon
                gwp:
                  type: number
                  format: float
                  example: 0.0
                  description: The GWP in lb CO2e/gallon
      400:
        description: Bad request
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: 'Mass is required'
      422:
        description: Unprocessable entity
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: 'Unit must be one of 'kghr', 'tons', 'tonnes''
      500:
        description: Unknown error
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: 'An unknown error occurred'
    """
    mass = request.args.get('mass', None)
    
    if mass is None:
        return make_response(
            jsonify({"error": "Mass is required"}), 400 # Bad request
        )
    
    try:
        mass = float(mass)
    except ValueError:
        return make_response(
            jsonify({"error": "Mass must be a number"}), 400 # Bad request
        )
    
    unit = request.args.get('unit', 'kghr')
    if unit not in ['kghr', 'tons', 'tonnes']:
        return make_response(
            jsonify({"error": "Unit must be one of 'kghr', 'tons', 'tonnes'"}), 422 # Unprocessable entity
        )
    
    try:
        kg_hr = fermentation_kg(mass, unit)
        ethanol, price, gwp = fermentation_calc(kg_hr)
        response_data = {
            "mass": kg_hr, # In kg/hr
            "ethanol": ethanol, # In MM gallons/year
            "price": price, # In $/gallon
            "gwp": gwp # In lb CO2e/gallon
        }
        return make_response(
            jsonify(response_data), 200 # Returns a success status code
        )
    except Exception as e:
        return make_response(
            jsonify({"error": str(e)}), 500 # Unknown error
        )
        
    
@fermentation_bp.route('/fermentation/county', methods=['GET'])
def fermentation_county_data():
    """
    Takes in a county name and returns the fermentation conversion efficiency for that county.
    
    URL Format - GET /fermentation/county?county_name=county_name
    ---
    tags:
      - Fermentation
    parameters:
      - name: county_name
        in: query
        type: string
        required: true
        description: The name of the county'
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
                mass:
                  type: number
                  format: float
                  example: 0.0
                  description: The mass of the feedstock in kg/hr
                ethanol:
                  type: number
                  format: float    
                  example: 0.0
                  description: The ethanol produced in MM gallons/year
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
                  example: 'County not found'
      500:
        description: Unexpected error
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: 'Unexpected error'
    """
    
    county_name = request.args.get('county_name', None)
    
    if not county_name:
        return make_response(
            jsonify({"error": "County name is required"}), 400 # Bad request
        )
        
    try:
      result = fermentation_county(county_name)
    except ValueError:
      return make_response(
          jsonify({"error": "County not found"}), 404 # Not found
      )
    except Exception as e:
      return make_response(
          jsonify({"error": str(e)}), 500 # Unexpected error
      )
    
    name, mass, ethanol, price, gwp = result
    response_data = {
        "county_name": name, # County name
        "mass": mass, # In kg/hr
        "ethanol": ethanol, # In MM gallons/year
        "price": price, # In $/gallon
        "gwp": gwp # In lb CO2e/gallon
    }
    return make_response(
        jsonify(response_data), 200 # Returns a success status code
    )
    
    
