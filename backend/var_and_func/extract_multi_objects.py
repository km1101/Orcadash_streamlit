"""
Extract time history data from multiple object types (Lines, Vessels, Buoys, Winches, Links)
"""
import OrcFxAPI
import pandas as pd
from .time_history import resolve_line_object_extra, resolve_period

def extract_time_history_multi_objects(file_path, object_names, variable_name, position_spec=None, period_spec=None):
    """
    Extract time history for multiple objects (Lines, Vessels, Buoys) from a single OrcaFlex model.
    
    Args:
        file_path: Path to .sim file
        object_names: List of object names (can be lines, vessels, buoys, winches, or links)
        variable_name: Variable to extract
        position_spec: Position specification (only applies to Lines, None for Vessels/Buoys/Winches/Links)
        period_spec: Period specification (default: None -> Whole Simulation)
                    Can be:
                    - None or "Whole Simulation" -> whole simulation
                    - "Build-up" -> stage 0
                    - "Stage 1" -> stage 1
                    - "Specified Period" -> requires period_from and period_to in a dict
                    - OrcFxAPI period object directly
    
    Returns:
        DataFrame with columns: 'Time' and one column per object name
    """
    try:
        model = OrcFxAPI.Model(file_path)
        
        # Resolve period specification
        if period_spec is None:
            period = None  # Default to whole simulation
        elif isinstance(period_spec, str):
            period = resolve_period(period_spec)
        elif isinstance(period_spec, dict):
            # Handle dict format: {"period": "Specified Period", "period_from": 1.0, "period_to": 2.0}
            period_name = period_spec.get("period", "Whole Simulation")
            if period_name == "Specified Period":
                period = resolve_period(
                    period_name,
                    period_spec.get("period_from"),
                    period_spec.get("period_to")
                )
            else:
                period = resolve_period(period_name)
        else:
            # Assume it's already an OrcFxAPI period object
            period = period_spec
        
        # Extract time series (respect period if specified)
        if period is None:
            time = model.general.TimeHistory("Time")
        else:
            time = model.general.TimeHistory("Time", period)
        
        data = {"Time": time}
        errors = []
        successful_extractions = 0
        
        for obj_name in object_names:
            try:
                obj = model[obj_name]
                
                # Determine object type
                obj_type = None
                for o in model.objects:
                    if o.Name == obj_name:
                        obj_type = o.type
                        break
                
                if obj_type is None:
                    error_msg = f"Object '{obj_name}' not found in model"
                    print(f"Error: {error_msg}")
                    errors.append(error_msg)
                    continue
                
                # Extract data based on object type
                if obj_type == OrcFxAPI.otLine:
                    from var_and_func.variables import is_end_load_variable, is_end_load_position_allowed
                    if is_end_load_variable(variable_name) and not is_end_load_position_allowed(position_spec):
                        error_msg = (
                            f"End Loads variable '{variable_name}' requires End A or End B "
                            f"(got position {position_spec!r})"
                        )
                        print(f"Error: {error_msg}")
                        errors.append(error_msg)
                        continue
                    # Lines need position specification
                    object_extra = resolve_line_object_extra(position_spec)
                    if period is None:
                        values = obj.TimeHistory(variable_name, objectExtra=object_extra)
                    else:
                        values = obj.TimeHistory(variable_name, period, objectExtra=object_extra)
                elif obj_type in (OrcFxAPI.otVessel, OrcFxAPI.ot6DBuoy, OrcFxAPI.ot3DBuoy, OrcFxAPI.otWinch, OrcFxAPI.otLink):
                    # Vessels, Buoys, Winches, and Links don't need position - use None
                    if period is None:
                        values = obj.TimeHistory(variable_name)
                    else:
                        values = obj.TimeHistory(variable_name, period)
                else:
                    print(f"Warning: Unknown object type for {obj_name}, trying default extraction")
                    if period is None:
                        values = obj.TimeHistory(variable_name)
                    else:
                        values = obj.TimeHistory(variable_name, period)
                
                # Validate that values were extracted
                if values is None or len(values) == 0:
                    error_msg = f"No data extracted for '{obj_name}' with variable '{variable_name}'"
                    print(f"Error: {error_msg}")
                    errors.append(error_msg)
                    continue
                
                data[obj_name] = values
                successful_extractions += 1
            except Exception as e:
                error_msg = f"Error processing {obj_name}: {str(e)}"
                print(f"Error: {error_msg}")
                errors.append(error_msg)
                continue
        
        df = pd.DataFrame(data)
        
        # If no objects were successfully extracted, raise an error
        if successful_extractions == 0:
            error_summary = "; ".join(errors) if errors else "Unknown error"
            raise ValueError(f"Failed to extract data for any objects. Errors: {error_summary}")
        
        # Log warnings for partial failures
        if len(errors) > 0:
            print(f"Warning: {len(errors)} object(s) failed extraction: {errors}")
        
        return df
    except Exception as e:
        print(f"Error processing {file_path} for multiple objects: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()
