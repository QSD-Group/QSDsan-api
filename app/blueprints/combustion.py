"""
What does this file do?
It creates a blueprint for the combustion endpoints in our app.
It imports the combustion service functions from app/services/combustion_service.py.
It defines the combustion_bp blueprint.
It defines two routes for the combustion_bp blueprint:
    1) /combustion/calc - For calculating the combustion-based electricity and emissions from a specified mass and waste type.
    2) /combustion/county - For calculating the combustion-based electricity and emissions for a given county and waste type.

What are the routes in this file?
/combustion/calc
/combustion/county

What does this file depend on?
app/services/combustion_service.py
- combustion_calc
- combustion_county

Where is this file used?
app/__init__.py
- app.register_blueprint(combustion_bp, url_prefix='/api/v1') # Registers the combustion_bp blueprint with the app.
"""

from flask import Blueprint, request, jsonify, make_response  # Flask Version 3.0.3
from app.services.combustion_service import (
    combustion_calc,
    combustion_county
)

combustion_bp = Blueprint('combustion_bp', __name__)

# ----------------------------------------
# Route 1: /combustion/calc
# ----------------------------------------
@combustion_bp.route('/combustion/calc', methods=['GET'])
def combustion_calc_data():
    """
    Takes in a mass, a unit of that mass, and a waste type, then returns:
      (1) The mass converted to kg/hr
      (2) The annual electricity production in MWh
      (3) The avoided emissions in million metric tonnes
      (4) The fraction of total NJ emissions avoided.
    
    URL Format - GET /combustion/calc?mass=mass&unit=unit&waste_type=waste_type
    ---
    tags:
      - Combustion
    parameters:
      - name: mass
        in: query
        type: number
        format: float
        required: true
        description: The mass of the feedstock
        example: 100.0
      - name: unit
        in: query
        type: string
        required: false
        description: The unit of the feedstock mass, defaults to 'kghr'
        example: 'kghr, tons, tonnes, mgd, m3d'
      - name: waste_type
        in: query
        type: string
        required: false
        description: The type of waste, defaults to 'sludge'
        example: 'sludge, food, fog, green, manure'
    responses:
      200:
        description: A successful response
        content:
          application/json:
            schema:
              type: object
              properties:
                mass:
                  type: float
                  example: 100.0
                  description: Mass in kg/hr
                waste_type:
                  type: string
                  example: 'sludge'
                  description: Type of waste used
                electricity:
                  type: float
                  example: 1.23
                  description: Annual electricity in MWh
                emissions:
                  type: float
                  example: 0.45
                  description: Avoided emissions in million metric tonnes
                percent:
                  type: float
                  example: 0.012
                  description: Fraction of total NJ emissions avoided
      400:
        description: Bad request
      422:
        description: Unprocessable entity
      500:
        description: Unexpected error
    """
    # 1) Get mass parameter
    mass_str = request.args.get('mass', None)
    if mass_str is None:
        return make_response(
            jsonify({"error": "Mass not provided"}), 400
        )

    try:
        mass = float(mass_str)
    except ValueError:
        return make_response(
            jsonify({"error": "Mass should be a number"}), 400
        )

    # 2) Get unit parameter
    unit = request.args.get('unit', 'kghr')
    valid_units = ['kghr', 'tons', 'tonnes', 'mgd', 'm3d']
    if unit not in valid_units:
        return make_response(
            jsonify({"error": f"Invalid unit. Must be one of {valid_units}"}), 422
        )

    # 3) Get waste_type parameter
    waste_type = request.args.get('waste_type', 'sludge')
    valid_waste_types = ['sludge', 'food', 'fog', 'green', 'manure']
    if waste_type not in valid_waste_types:
        return make_response(
            jsonify({"error": f"Invalid waste_type. Must be one of {valid_waste_types}"}), 422
        )

    # 4) Convert mass to kg/hr if needed
    #    This logic parallels the older approach (manually converting),
    #    or you could adapt a helper function if you had one.
    #    For now, let's do it here inline:
    if unit == 'kghr':
        mass_kg_hr = mass
    elif unit == 'tons':      # short tons/year -> kg/hr
        # older approach used: mass * 907.185 / (365*24)
        mass_kg_hr = mass * 907.185 / (365 * 24)
    elif unit == 'tonnes':    # metric tonnes/year -> kg/hr
        mass_kg_hr = mass * 1000 / (365 * 24)
    elif unit == 'mgd':       # MGD -> kg/hr
        # 1 million gallons/day = 1e6 gallons/day
        # 1 gallon ~ 3.78541 kg water
        # so mgd to kg/day = mgd * 1e6 * 3.78541
        # then to kg/hr, divide by 24
        mass_kg_hr = mass * 1e6 * 3.78541 / 24
    elif unit == 'm3d':       # m^3/day -> kg/hr
        # 1 m^3 of water ~ 1000 kg
        # If mass is in m^3/day, multiply by 1000 -> kg/day
        # Then /24 -> kg/hr
        mass_kg_hr = mass * 1000 / 24
    else:
        # This shouldn't be reached because of the earlier check
        return make_response(
            jsonify({"error": f"Invalid unit. Must be one of {valid_units}"}), 422
        )

    # 5) Calculate results using combustion_calc from the service
    try:
        result = combustion_calc(mass_kg_hr, waste_type)
        if not result:
            return make_response(
                jsonify({"error": "Unexpected error in combustion_calc"}), 500
            )
        # Unpack the results
        wt, mass_kg_hr2, electricity, emissions, percent = result

        response_data = {
            "mass": mass_kg_hr2,          # in kg/hr
            "waste_type": wt,
            "electricity": electricity,    # MWh
            "emissions": emissions,       # million metric tonnes
            "percent": percent            # fraction of total NJ emissions
        }
        return make_response(jsonify(response_data), 200)

    except (TypeError, ValueError) as e:
        return make_response(
            jsonify({"error": str(e)}), 422
        )
    except Exception as e:
        return make_response(
            jsonify({"error": f"Unexpected error: {str(e)}"}), 500
        )


# ----------------------------------------
# Route 2: /combustion/county
# ----------------------------------------
@combustion_bp.route('/combustion/county', methods=['GET'])
def combustion_county_data():
    """
    Takes in a county name and a waste type, then returns:
      (1) The county name (as found in the data set)
      (2) The mass (kg/hr) associated with that county for the specified waste
      (3) The annual electricity production in MWh
      (4) The avoided emissions in million metric tonnes
      (5) The fraction of total NJ emissions avoided
    
    URL Format - GET /combustion/county?county_name=county_name&waste_type=waste_type
    ---
    tags:
      - Combustion
    parameters:
      - name: county_name
        in: query
        type: string
        required: true
        description: The name of the county
        example: 'Essex'
      - name: waste_type
        in: query
        type: string
        required: false
        description: The type of waste, defaults to sludge
        example: 'sludge, food, fog, green, manure'
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
                  example: 'Essex'
                waste_type:
                  type: string
                  example: 'sludge'
                mass:
                  type: float
                  example: 100.0
                electricity:
                  type: float
                  example: 1.23
                emissions:
                  type: float
                  example: 0.45
                percent:
                  type: float
                  example: 0.012
      400:
        description: Bad request, missing county_name
      404:
        description: Not found
      422:
        description: Unprocessable entity
      500:
        description: Unexpected error
    """
    # 1) Get the county_name parameter
    county_name = request.args.get('county_name', None)
    if not county_name:
        return make_response(
            jsonify({"error": "County name not provided"}), 400
        )

    # 2) Get waste_type parameter
    waste_type = request.args.get('waste_type', 'sludge')
    valid_waste_types = ['sludge', 'food', 'fog', 'green', 'manure']
    if waste_type not in valid_waste_types:
        return make_response(
            jsonify({"error": f"Invalid waste_type. Must be one of {valid_waste_types}"}), 422
        )

    # 3) Call combustion_county from the service
    try:
        result = combustion_county(county_name, waste_type)
        if result is None:
            return make_response(
                jsonify({"error": "County not found"}), 404
            )
        name_final, wt, mass, electricity, emissions, percent = result

        response_data = {
            "county_name": name_final,
            "waste_type": wt,
            "mass": mass,
            "electricity": electricity,
            "emissions": emissions,
            "percent": percent
        }
        return make_response(jsonify(response_data), 200)

    except (TypeError, ValueError) as e:
        return make_response(
            jsonify({"error": str(e)}), 422
        )
    except Exception as e:
        return make_response(
            jsonify({"error": f"Unexpected error: {str(e)}"}), 500
        )
