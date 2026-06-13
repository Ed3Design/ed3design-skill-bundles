#!/usr/bin/env python3
"""
Generiert Fusion360 Python Code für User Parameters basierend auf einer Parametertabelle.

Usage:
    python generate_parameters.py parameters.json output.py
"""

import json
import sys
from typing import Dict, List


def generate_parameter_code(parameters: List[Dict]) -> str:
    """
    Generiert Fusion360 Python Code für User Parameters.
    
    Args:
        parameters: Liste von Dicts mit 'name', 'value', 'unit', 'comment'
    
    Returns:
        Python Code String
    """
    code = """import adsk.core, adsk.fusion

def create_parameters():
    '''Erstellt User Parameters im aktiven Design'''
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    
    if not design:
        return False
    
    userParams = design.userParameters
    
    # Bestehende Parameter löschen (optional - auskommentieren falls gewünscht)
    # for i in range(userParams.count - 1, -1, -1):
    #     userParams.item(i).deleteMe()
    
"""
    
    for param in parameters:
        name = param['name']
        value = param['value']
        unit = param.get('unit', 'mm')
        comment = param.get('comment', '')
        
        # Wert-Typ erkennen
        if isinstance(value, str) and any(op in value for op in ['+', '-', '*', '/', '(']):
            # Formel
            code += f"    # {comment}\n" if comment else ""
            code += f"    userParams.add('{name}', adsk.core.ValueInput.createByString('{value}'), '{unit}', '{comment}')\n\n"
        else:
            # Numerischer Wert
            code += f"    # {comment}\n" if comment else ""
            code += f"    userParams.add('{name}', adsk.core.ValueInput.createByReal({value}), '{unit}', '{comment}')\n\n"
    
    code += """    return True

def run(context):
    try:
        if create_parameters():
            print("✅ Parameter erfolgreich erstellt")
        else:
            print("❌ Kein aktives Design gefunden")
    except Exception as e:
        print(f"❌ Fehler: {str(e)}")
"""
    
    return code


def main():
    if len(sys.argv) != 3:
        print("Usage: python generate_parameters.py parameters.json output.py")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # JSON einlesen
    with open(input_file, 'r', encoding='utf-8') as f:
        parameters = json.load(f)
    
    # Code generieren
    code = generate_parameter_code(parameters)
    
    # Code schreiben
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(code)
    
    print(f"✅ Fusion360 Parameter-Code generiert: {output_file}")


if __name__ == "__main__":
    main()
