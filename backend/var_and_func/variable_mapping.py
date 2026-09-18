"""
Parse Variables_list.csv to create a mapping of variables to object types
"""
import csv
import os

def parse_variables_csv(csv_path=None):
    """
    Parse Variables_list.csv to create a mapping of variables to object types.
    
    CSV format:
    - First row: headers (Buoy, Vessel, Environment, Line, Winch, Link)
    - Subsequent rows: variables listed under columns they apply to
    
    Returns:
        dict: {variable_name: [object_types]}
    """
    if csv_path is None:
        # Default path relative to this file
        csv_path = os.path.join(os.path.dirname(__file__), 'Variables_list.csv')
    
    variable_to_types = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)  # Read header row
            
            # Map column indices to object types
            # CSV columns: Buoy, Vessel, Environment, Line, Winch, Link
            column_to_type = {
                0: ['6DBuoy', '3DBuoy'],  # Buoy applies to both 6D and 3D buoys
                1: ['Vessel'],
                2: ['Environment'],
                3: ['Line'],
                4: ['Winch'],
                5: ['Link']
            }
            
            for row in reader:
                for col_idx, var_name in enumerate(row):
                    if var_name and var_name.strip():  # Skip empty cells
                        var_name = var_name.strip()
                        if col_idx in column_to_type:
                            object_types = column_to_type[col_idx]
                            if var_name not in variable_to_types:
                                variable_to_types[var_name] = []
                            # Add object types (avoid duplicates)
                            for obj_type in object_types:
                                if obj_type not in variable_to_types[var_name]:
                                    variable_to_types[var_name].append(obj_type)
    
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        import traceback
        traceback.print_exc()
    
    return variable_to_types

def get_variables_for_object_types(object_types):
    """
    Get list of variables valid for the given object types.
    
    Args:
        object_types: List of object types (e.g., ['Vessel', '6DBuoy'])
    
    Returns:
        List of variable names
    """
    mapping = parse_variables_csv()
    valid_variables = []
    
    for var_name, valid_types in mapping.items():
        # Variable is valid if it applies to any of the requested object types
        if any(obj_type in valid_types for obj_type in object_types):
            valid_variables.append(var_name)
    
    return sorted(valid_variables)

if __name__ == '__main__':
    # Test the parser
    mapping = parse_variables_csv()
    print(f"Parsed {len(mapping)} variables")
    print("\nSample mappings:")
    for var_name, types in list(mapping.items())[:10]:
        print(f"  {var_name}: {types}")
