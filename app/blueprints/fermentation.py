"""
Fermentation Blueprint for Flask API

- Contains routes for fermentation calculations.
- Supports mass-to-ethanol conversion and county-based calculations.

Dependencies:
- fermentation_service.py
  - fermentation_convert_feedstock_kg_hr
  - fermentation_calc
  - fermentation_county

Routes:
- /fermentation/calc (GET)
- /fermentation/county (GET)
"""

from flask import Blueprint, request, jsonify, make_response
from app.services.fermentation_service import (
    fermentation_calc, fermentation_county, fermentation_convert_feedstock_kg_hr as fermentation_kg
)

fermentation_bp = Blueprint('fermentation_bp', __name__)

@fermentation_bp.route('/fermentation/calc', methods=['GET'])
def fermentation_calc_data():
    """
    Convert mass input to ethanol production and related metrics.
    Takes in a mass of feed stock, a unit of that mass and returns:
    (1) mass of the feedstock in kg/hr,
    (2) ethanol produced in MM gallons/year,
    (3) price of ethanol in $/gallon,
    (4) greenhouse gas emissions in lb CO2e/gallon.
    
    GET /fermentation/calc?mass=mass&unit=unit
    
    ---
    tags:
      - Fermentation
    parameters:
      - name: mass
        in: query
        type: number
        format: float
        required: true
        description: Mass of the feedstock.
        example: 100.0
      - name: unit
        in: query
        type: string
        required: true
        description: Unit of the mass ('kghr', 'tons', 'tonnes').
        example: "tons"
    responses:
      200:
        description: Successful response.
        content:
          application/json:
            schema:
              type: object
              properties:
                mass:
                  type: number
                  format: float
                  example: 100.0
                  description: Mass of the feedstock in kg/hr.
                ethanol:
                  type: number
                  format: float
                  example: 0.5
                  description: Ethanol produced in MM gallons/year.
                price:
                  type: number
                  format: float
                  example: 2.5
                  description: Ethanol price in $/gallon.
                gwp:
                  type: number
                  format: float
                  example: 10.0
                  description: Greenhouse gas emissions in lb CO2e/gallon.
      400:
        description: Bad request.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Mass is required"
      422:
        description: Unprocessable entity.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Unit must be one of ['kghr', 'tons', 'tonnes']"
      500:
        description: Internal server error.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "An unknown error occurred"
    """
    
    mass = request.args.get('mass')
    unit = request.args.get('unit', 'kghr')

    if mass is None:
        return make_response(jsonify({"message": "Mass is required"}), 400)

    try:
        mass = float(mass)
    except ValueError:
        return make_response(jsonify({"message": "Mass must be a number"}), 400)

    if unit not in ['kghr', 'tons', 'tonnes']:
        return make_response(jsonify({"message": "Unit must be one of ['kghr', 'tons', 'tonnes']"}), 422)

    try:
        kg_hr = fermentation_kg(mass, unit)
        ethanol, price, gwp = fermentation_calc(kg_hr)
        return make_response(
            jsonify({
                "mass": kg_hr,
                "ethanol": ethanol,
                "price": price,
                "gwp": gwp
            }), 200
        )
    except Exception as e:
        return make_response(jsonify({"message": str(e)}), 500)


@fermentation_bp.route('/fermentation/county', methods=['GET'])
def fermentation_county_data():
    """
    Calculate ethanol production and related metrics for a given county.
    Takes in a county name and returns:
    (1) mass of the feedstock in kg/hr,
    (2) ethanol produced in MM gallons/year,
    (3) price of ethanol in $/gallon,
    (4) greenhouse gas emissions in lb CO2e/gallon.
    
    GET /fermentation/county?county_name=county_name
    
    ---
    tags:
      - Fermentation
    parameters:
      - name: county_name
        in: query
        type: string
        required: true
        description: Name of the county.
        example: "Atlantic"
    responses:
      200:
        description: Successful response.
        content:
          application/json:
            schema:
              type: object
              properties:
                county_name:
                  type: string
                  example: "Atlantic"
                mass:
                  type: number
                  format: float
                  example: 200.0
                  description: Mass of the feedstock in kg/hr.
                ethanol:
                  type: number
                  format: float
                  example: 1.2
                  description: Ethanol produced in MM gallons/year.
                price:
                  type: number
                  format: float
                  example: 2.5
                  description: Ethanol price in $/gallon.
                gwp:
                  type: number
                  format: float
                  example: 8.0
                  description: Greenhouse gas emissions in lb CO2e/gallon.
      400:
        description: Bad request.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "County name is required"
      404:
        description: County not found.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "County not found"
      500:
        description: Internal server error.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "An unknown error occurred"
    """

    county_name = request.args.get('county_name')

    if not county_name:
        return make_response(jsonify({"message": "County name is required"}), 400)

    try:
        name, mass, ethanol, price, gwp = fermentation_county(county_name)
        return make_response(
            jsonify({
                "county_name": name,
                "mass": mass,
                "ethanol": ethanol,
                "price": price,
                "gwp": gwp
            }), 200
        )
    except ValueError:
        return make_response(jsonify({"message": "County not found"}), 404)
    except Exception as e:
        return make_response(jsonify({"message": str(e)}), 500)
