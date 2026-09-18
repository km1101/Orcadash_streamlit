Range_Graph_variable_dict = {
    "Position": ["X", "Y", "Z", "Expansion Factor"],
    "Motions": [
        "Velocity", "GX-Velocity", "GY-Velocity", "GZ-Velocity", 
        "Acceleration", "GX-Acceleration", "GY-Acceleration", "GZ-Acceleration", 
        "Acceleration rel. g", "x-Acceleration rel. g", "y-Acceleration rel. g", "z-Acceleration rel. g"
    ],
    "Angles": ["Azimuth", "Declination", "Gamma", "Twist", "Fluid Incidence Angle", "Ez-Angle", "Exy-Angle", "Ezx-Angle", "Ezy-Angle"],
    "Forces": ["Effective Tension", "Normalised Tension", "Contents Density", "Shear Force", "x-Shear Force", "y-Shear Force", "Shear Force component", "In-plane Shear Force", "Out-of-plane Shear Force"],
    "Moments": ["Bend Moment", "x-Bend Moment", "y-Bend Moment", "Bend Moment component", "In-plane Bend Moment", "Out-of-plane Bend Moment", "Curvature", "Normalised Curvature", "x-Curvature", "y-Curvature", "Curvature component", "In-plane Curvature", "Out-of-plane Curvature", "Bend Radius", "x-Bend Radius", "y-Bend Radius", "Bend Radius component", "In-plane Bend Radius", "Out-of-plane Bend Radius"],
    "Contact": ["Line Clearance", "Line Centreline Clearance", "Seabed Clearance", "Vertical Seabed Clearance", "Line Clash Force", "Line Clash Energy", "Solid Contact Force", "Seabed Normal Penetration/D", "Seabed Normal Resistance", "Seabed Normal Resistance/D"],
    "Pipe Stress/Strain": ["Direct Tensile Strain", "Max Bending Strain", "Worst ZZ Strain", "ZZ Strain", "Max von Mises Stress", "Max Bending Stress", "Worst ZZ Stress", "Direct Tensile Stress", "Worst Hoop Stress", "Max xy-Shear Stress", "Internal Pressure", "External Pressure", "Net Internal Pressure", "von Mises Stress", "RR Stress", "CC Stress", "ZZ Stress", "RC Stress", "RZ Stress", "CZ Stress"],
    "Code Checks": ["API RP 2RD Stress", "API RP 2RD Utilisation", "API RP 1111 LLD", "API RP 1111 CLD", "API RP 1111 BEP", "API RP 1111 Max Combined", "DNV OS F101 Disp. Controlled", "DNV OS F101 Load Controlled", "DNV OS F101 Simplified Strain", "DNV OS F101 Simplified Stress", "DNV OS F101 Tension Utilisation", "DNV OS F201 LRFD", "DNV OS F201 WSD", "PD 8010 Allowable Stress Check", "PD 8010 Axial Compression Check", "PD 8010 Bending Check", "PD 8010 Torsion Check", "PD 8010 Load Combinations Check", "PD 8010 Bending Strain Check"],
    "Fluid Loads": ["Relative Velocity", "Normal Relative Velocity", "Axial Relative Velocity", "Strouhal Frequency", "Reynolds number", "x-Drag Coefficient", "y-Drag Coefficient", "z-Drag Coefficient", "Lift Coefficient", "Sea Surface Z", "Depth", "Sea Surface Clearance", "Proportion Wet"]
}
variables_dict = {
    "Position": {
        # Common position variables (Lines, Vessels, Buoys)
        "X": "m",
        "Y": "m", 
        "Z": "m",
        "Rotation 1": "°",
        "Rotation 2": "°",
        "Rotation 3": "°",
        "Azimuth": "°",
        "Declination": "°",
        "Sea Surface Z": "m",
        "Sea Surface Clearance": "m",
        # Line-specific
        "Expansion Factor": "-",
        # Vessel-specific
        "Primary X": "m",
        "Primary Y": "m",
        "Primary Z": "m",
        "Primary Rotation 1": "°",
        "Primary Rotation 2": "°",
        "Primary Rotation 3": "°",
        # Buoy-specific
        "Dry Length": "m",
        # Link-specific (Length also shared with Winch — see the dedicated
        # "Winch" category for Winch's full variable set, incl. Stretched Length)
        "Length": "m",
        "End A X": "m",
        "End A Y": "m",
        "End A Z": "m",
        "End B X": "m",
        "End B Y": "m",
        "End B Z": "m"
    },
    "Motions": {
        # Common motion variables (Lines, Vessels, Buoys)
        "Velocity": "m/s",
        "GX-Velocity": "m/s",
        "GY-Velocity": "m/s", 
        "GZ-Velocity": "m/s",
        "Acceleration": "m/s²",
        "GX-Acceleration": "m/s²",
        "GY-Acceleration": "m/s²",
        "GZ-Acceleration": "m/s²",
        "Acceleration rel. g": "g",
        "x-Acceleration rel. g": "g",
        "y-Acceleration rel. g": "g",
        "z-Acceleration rel. g": "g",
        # Vessel and Buoy specific
        "Angular Velocity": "rad/s",
        "x-Angular Velocity": "rad/s",
        "y-Angular Velocity": "rad/s",
        "z-Angular Velocity": "rad/s",
        "Angular Acceleration": "rad/s²",
        "x-Angular Acceleration": "rad/s²",
        "y-Angular Acceleration": "rad/s²",
        "z-Angular Acceleration": "rad/s²",
        # Buoy-specific
        "Sea Velocity": "m/s",
        "Sea X Velocity": "m/s",
        "Sea Y Velocity": "m/s",
        "Sea Z Velocity": "m/s",
        "Sea Acceleration": "m/s²",
        "Sea X Acceleration": "m/s²",
        "Sea Y Acceleration": "m/s²",
        "Sea Z Acceleration": "m/s²"
    },
    "Angles": {
        "Azimuth": "°",
        "Declination": "°",
        "Gamma": "°",
        "Twist": "°",
        "Fluid Incidence Angle": "°",
        "Ez-Angle": "°",
        "Exy-Angle": "°",
        "Ezx-Angle": "°",
        "Ezy-Angle": "°"
    },
    "Forces": {
        # Line-specific forces
        "Effective Tension": "KN",
        # Link-specific (Tension also shared with Winch — see the dedicated
        # "Winch" category for Winch's Connection Force variables)
        "Tension": "KN",
        "Normalised Tension": "-",
        "Contents Density": "kg/m³",
        "Shear Force": "KN",
        "x-Shear Force": "KN",
        "y-Shear Force": "KN",
        "Shear Force component": "KN",
        "In-plane Shear Force": "N",
        "Out-of-plane Shear Force": "KN",
        # Vessel-specific forces
        "Total Force": "N",
        "Total Lx-Force": "N",
        "Total Ly-Force": "N",
        "Total Lz-Force": "N",
        "Connections Force": "N",
        "Connections Lx-Force": "N",
        "Connections Ly-Force": "N",
        "Connections Lz-Force": "N",
        "Connections GX-Force": "N",
        "Connections GY-Force": "N",
        "Connections GZ-Force": "N",
        "Hydrostatic Stiffness Force": "N",
        "Hydrostatic Stiffness Lx-Force": "N",
        "Hydrostatic Stiffness Ly-Force": "N",
        "Hydrostatic Stiffness Lz-Force": "N",
        "Wave (1st order) Force": "N",
        "Wave (1st order) Lx-Force": "N",
        "Wave (1st order) Ly-Force": "N",
        "Wave (1st order) Lz-Force": "N",
        "Wave Drift (2nd order) Force": "N",
        "Wave Drift (2nd order) Lx-Force": "N",
        "Wave Drift (2nd order) Ly-Force": "N",
        "Wave Drift (2nd order) Lz-Force": "N",
        "Added Mass & Damping Force": "N",
        "Added Mass & Damping Lx-Force": "N",
        "Added Mass & Damping Ly-Force": "N",
        "Added Mass & Damping Lz-Force": "N",
        "Current Force": "N",
        "Current Lx-Force": "N",
        "Current Ly-Force": "N",
        "Current Lz-Force": "N",
        "Wind Force": "N",
        "Wind Lx-Force": "N",
        "Wind Ly-Force": "N",
        "Wind Lz-Force": "N",
        # Buoy-specific forces
        "Applied Force": "N",
        "Applied Lx-Force": "N",
        "Applied Ly-Force": "N",
        "Applied Lz-Force": "N",
        "Force": "N",
        "Lx-Force": "N",
        "Ly-Force": "N",
        "Lz-Force": "N",
        "GX-Force": "N",
        "GY-Force": "N",
        "GZ-Force": "N"
    },
    "Moments": {
        # Line-specific moments
        "Bend Moment": "N·m",
        "x-Bend Moment": "N·m",
        "y-Bend Moment": "N·m",
        "Bend Moment component": "N·m",
        "In-plane Bend Moment": "N·m",
        "Out-of-plane Bend Moment": "N·m",
        "Curvature": "1/m",
        "Normalised Curvature": "-",
        "x-Curvature": "1/m",
        "y-Curvature": "1/m",
        "Curvature component": "1/m",
        "In-plane Curvature": "1/m",
        "Out-of-plane Curvature": "1/m",
        "Bend Radius": "m",
        "x-Bend Radius": "m",
        "y-Bend Radius": "m",
        "Bend Radius component": "m",
        "In-plane Bend Radius": "m",
        "Out-of-plane Bend Radius": "m",
        # Vessel-specific moments
        "Total Moment": "N·m",
        "Total Lx-Moment": "N·m",
        "Total Ly-Moment": "N·m",
        "Total Lz-Moment": "N·m",
        "Connections Moment": "N·m",
        "Connections Lx-Moment": "N·m",
        "Connections Ly-Moment": "N·m",
        "Connections Lz-Moment": "N·m",
        "Connections GX-Moment": "N·m",
        "Connections GY-Moment": "N·m",
        "Connections GZ-Moment": "N·m",
        "Hydrostatic Stiffness Moment": "N·m",
        "Hydrostatic Stiffness Lx-Moment": "N·m",
        "Hydrostatic Stiffness Ly-Moment": "N·m",
        "Hydrostatic Stiffness Lz-Moment": "N·m",
        "Wave (1st order) Moment": "N·m",
        "Wave (1st order) Lx-Moment": "N·m",
        "Wave (1st order) Ly-Moment": "N·m",
        "Wave (1st order) Lz-Moment": "N·m",
        "Wave Drift (2nd order) Moment": "N·m",
        "Wave Drift (2nd order) Lx-Moment": "N·m",
        "Wave Drift (2nd order) Ly-Moment": "N·m",
        "Wave Drift (2nd order) Lz-Moment": "N·m",
        "Added Mass & Damping Moment": "N·m",
        "Added Mass & Damping Lx-Moment": "N·m",
        "Added Mass & Damping Ly-Moment": "N·m",
        "Added Mass & Damping Lz-Moment": "N·m",
        "Current Moment": "N·m",
        "Current Lx-Moment": "N·m",
        "Current Ly-Moment": "N·m",
        "Current Lz-Moment": "N·m",
        "Wind Moment": "N·m",
        "Wind Lx-Moment": "N·m",
        "Wind Ly-Moment": "N·m",
        "Wind Lz-Moment": "N·m",
        # Buoy-specific moments
        "Applied Moment": "N·m",
        "Applied Lx-Moment": "N·m",
        "Applied Ly-Moment": "N·m",
        "Applied Lz-Moment": "N·m",
        "Moment": "N·m",
        "Lx-Moment": "N·m",
        "Ly-Moment": "N·m",
        "Lz-Moment": "N·m",
        "GX-Moment": "N·m",
        "GY-Moment": "N·m",
        "GZ-Moment": "N·m"
    },
    "Contact": {
        "Line Clearance": "m",
        "Line Centreline Clearance": "m",
        "Seabed Clearance": "m",
        "Vertical Seabed Clearance": "m",
        "Line Clash Force": "N",
        "Line Clash Energy": "J",
        "Solid Contact Force": "N",
        "Seabed Normal Penetration/D": "-",
        "Seabed Normal Resistance": "N",
        "Seabed Normal Resistance/D": "N/m"
    },
    "Pipe Stress/Strain": {
        "Direct Tensile Strain": "-",
        "Max Bending Strain": "-",
        "Worst ZZ Strain": "-",
        "ZZ Strain": "-",
        "Max von Mises Stress": "Pa",
        "Max Bending Stress": "Pa",
        "Worst ZZ Stress": "Pa",
        "Direct Tensile Stress": "Pa",
        "Worst Hoop Stress": "Pa",
        "Max xy-Shear Stress": "Pa",
        "Internal Pressure": "Pa",
        "External Pressure": "Pa",
        "Net Internal Pressure": "Pa",
        "von Mises Stress": "Pa",
        "RR Stress": "Pa",
        "CC Stress": "Pa",
        "ZZ Stress": "Pa",
        "RC Stress": "Pa",
        "RZ Stress": "Pa",
        "CZ Stress": "Pa"
    },
    "Code Checks": {
        "API RP 2RD Stress": "Pa",
        "API RP 2RD Utilisation": "-",
        "API RP 1111 LLD": "-",
        "API RP 1111 CLD": "-",
        "API RP 1111 BEP": "-",
        "API RP 1111 Max Combined": "-",
        "DNV OS F101 Disp. Controlled": "-",
        "DNV OS F101 Load Controlled": "-",
        "DNV OS F101 Simplified Strain": "-",
        "DNV OS F101 Simplified Stress": "Pa",
        "DNV OS F101 Tension Utilisation": "-",
        "DNV OS F201 LRFD": "-",
        "DNV OS F201 WSD": "-",
        "PD 8010 Allowable Stress Check": "-",
        "PD 8010 Axial Compression Check": "-",
        "PD 8010 Bending Check": "-",
        "PD 8010 Torsion Check": "-",
        "PD 8010 Load Combinations Check": "-",
        "PD 8010 Bending Strain Check": "-"
    },
    "Fluid Loads": {
        "Relative Velocity": "m/s",
        "Normal Relative Velocity": "m/s",
        "Axial Relative Velocity": "m/s",
        "Strouhal Frequency": "Hz",
        "Reynolds number": "-",
        "x-Drag Coefficient": "-",
        "y-Drag Coefficient": "-",
        "z-Drag Coefficient": "-",
        "Lift Coefficient": "-",
        "Sea Surface Z": "m",
        "Depth": "m",
        "Sea Surface Clearance": "m",
        "Proportion Wet": "-"
    },
    # Line + Time History only; valid at End A / End B (not Range Graph / arc length).
    "End Loads": {
        "End force": "N",
        "End moment": "N·m",
        "Bend restrictor load": "N",
    },
    "End Loads (Global)": {
        "End GX force": "N",
        "End GY force": "N",
        "End GZ force": "N",
        "Horizontal end force": "N",
        "End GX moment": "N·m",
        "End GY moment": "N·m",
        "End GZ moment": "N·m",
    },
    "End Loads (Local)": {
        "End Lx force": "N",
        "End Ly force": "N",
        "End Lz force": "N",
        "End Lx moment": "N·m",
        "End Ly moment": "N·m",
        "End Lz moment": "N·m",
    },
    "End loads (end axes)": {
        "End Ex force": "N",
        "End Ey force": "N",
        "End Ez force": "N",
        "End Ex moment": "N·m",
        "End Ey moment": "N·m",
        "End Ez moment": "N·m",
    },
    "Winch": {
        # Winch-exclusive category — mirrors how "Environment *" categories
        # isolate Environment's variables from the shared Line/Vessel/Buoy
        # categories above. X/Y/Z/Velocity/Azimuth/Declination/Tension/Length
        # are also legitimately shared with Vessel/Buoy/Link (kept untouched
        # in their original categories above); Stretched Length and the
        # Connection *-Force variables exist only for Winch.
        "X": "m",
        "Y": "m",
        "Z": "m",
        "Tension": "KN",
        "Length": "m",
        "Stretched Length": "m",
        "Velocity": "m/s",
        "Azimuth": "°",
        "Declination": "°",
        "Connection Force": "N",
        "Connection GX-Force": "N",
        "Connection GY-Force": "N",
        "Connection GZ-Force": "N"
    },
    "Environment Position": {
        "Elevation": "m"
    },
    "Environment": {
        "Velocity": "m/s",
        "X Velocity": "m/s",
        "Y Velocity": "m/s",
        "Z Velocity": "m/s",
        "Acceleration": "m/s²",
        "X Acceleration": "m/s²",
        "Y Acceleration": "m/s²",
        "Z Acceleration": "m/s²",
        "current speed": "m/s",
        "current direction": "°",
        "wind speed": "m/s",
        "wind direction": "°",
        "static pressure": "Pa",
        "density": "kg/m³"
    },

    "Link": {
        "Tension": "KN",
        "Length": "m",
        "Stretched Length": "m",
        "End A X": "m",
        "End A Y": "m",
        "End A Z": "m",
        "End B X": "m",
        "End B Y": "m",
        "End B Z": "m"
    }
}

# Line Time-History end-connection results — End A / End B only (not Range Graph).
END_LOAD_CATEGORIES = (
    "End Loads",
    "End Loads (Global)",
    "End Loads (Local)",
    "End loads (end axes)",
)


def is_end_load_category(category):
    return category in END_LOAD_CATEGORIES


def end_load_variable_names():
    names = set()
    for category in END_LOAD_CATEGORIES:
        names.update(variables_dict.get(category, {}).keys())
    return names


def is_end_load_variable(variable_name):
    if not variable_name:
        return False
    return variable_name in end_load_variable_names()


def is_end_load_position_allowed(position_spec):
    """True when position is End A / End B (or default None → End A)."""
    if position_spec is None:
        return True
    if isinstance(position_spec, str):
        key = position_spec.strip().lower().replace(" ", "")
        return key in ("enda", "a", "endb", "b")
    return False


def get_variable_units(variable_name):
    """Return units for a variable name, or None if unknown."""
    for _category, variables in variables_dict.items():
        if variable_name in variables:
            return variables[variable_name]
    return None
