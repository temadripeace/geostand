import io
import os
import re
import json
import tempfile
import zipfile
import chardet
import unicodedata
import pandas as pd
import streamlit as st
import geopandas as gpd
from shapely import wkt
import xml.etree.ElementTree as ET
from shapely.validation import make_valid
from shapely.ops import transform
from shapely.geometry import shape, Point, Polygon, MultiPolygon, MultiPoint, LineString
#======================================================================================================================================
# SIDEBAR PAGE SETTUP FOR THE STREAMLIT APP
#======================================================================================================================================
st.set_page_config(
    page_title="Geospatial Data Cleaning Tool",
    page_icon="sucafina.svg",
    layout="wide"
)

# Sidebar content (dynamic width)
st.sidebar.markdown(
    """
    <div style="
        font-size:15px;
        font-family:'Poppins', sans-serif;
        font-weight:500;
        line-height:2;
        color: var(--brand-color);
        text-align:justify;
    ">

    <b> TOOL OVERVIEW:</b>

    This tool performs geospatial data cleaning and standardisation, enabling seamless integration with Meridia and other geospatial platforms. It supports multiple file formats, including CSV, GeoJSON, KML, Excel, and ZIP archives, as well as various character encodings such as UTF-8, Latin1, and Windows-1252, ensuring special characters are handled correctly during data processing.
    
    
    <b> KEY FEATURES:</b>
    <ul>
    <li>Cleans special characters and prevents encoding issues.</li>
    <li>Converts geometry columns into valid WKT format.</li>
    <li>Closes POLYGON and MULTIPOLYGON rings.</li>
    <li>Arranges coordinates in Longitude/Latitude format.</li>
    <li>Removes Z-values to keep geometries in 2D.</li>
    <li>Formats coordinates to six decimal places.</li>
    <li>Computes Plot Area for Polygons & Multipolygons.</li>
    <li>Cleans small spikes and self-intersections.</li>
    <li>Maps data fields to Sucafina's standardised Geodata Schema.</li>
    <li>Exports standardised data to CSV, Excel, KML, or GeoJSON formats.</li>
    </ul>

    <b> REQUIRED GEOMETRY COLUMN NAMES</b>
    

    <li><b>Longitude / Latitude (Separate Columns):</b>
    lon, lat, Lon, Lat, LON, LAT, longitude, latitude, Longitude, Latitude, LONGITUDE, LATITUDE<br></li>

    <li><b>Single Column Points:</b>
    point, Point, POINT, gps_point, Gps_Point, GPS_POINT, plot_gps_point, Plot_Gps_Point, PLOT_GPS_POINT<br></li>

    <li><b>Polygons/Multipolygons:</b>
    polygon, Polygon, POLYGON, gps_polygon, Gps_Polygon, GPS_POLYGON, plot_gps_polygon, Plot_Gps_Polygon, PLOT_GPS_POLYGON</li>

    </div>
    """,
    unsafe_allow_html=True
)

#======================================================================================================================================

# MAIN TOOL PAGE SETTUP FOR THE STREAMLIT APP
#======================================================================================================================================
st.markdown("""
<style>
:root {
    --brand-color: #15767f;
    --brand-hover: #246b45;
    --brand-dark: #218838;
}

@media (prefers-color-scheme: dark) {
    :root {
        --brand-color: #4dd0e1;
        --brand-hover: #26c6da;
        --brand-dark: #1ba9b8;
    }
}

.block-container {
    padding-top: 0rem;
    padding-bottom: 0rem;
    margin-top: 0rem;
}

.fixed-header {
    position: absolute;
    top: 3rem;
    left: 0;       
    width: 100%;
    z-index: 9999;
    text-align: center;
    padding: 2px 2px 2px 2px;
    border-bottom: 2px solid var(--brand-color);
}

.fixed-header img {
    display: block;
    margin: 0 auto;
    width: 200px;  
    height: auto;
}

.fixed-header h1 {
    font-family: 'Poppins', sans-serif;
    color: var(--brand-color);
    font-size: 26px;
    margin: 0 0 0 0;
}

.content {
    margin-top: 270px;
}
            
.content-headings {
    font-family: 'Poppins', sans-serif;
    color: var(--brand-color);
    font-size: 24px;
    font-weight: bold;
}
            
@media (max-width: 1200px) {
    .fixed-header {
        top: 3rem;
        padding: 2px 2px 2px 2px;
        border-bottom-width: 2px;
    }

    .fixed-header img {
        width: 200px;
    }

    .fixed-header h1 {
        font-size: 26px;
        margin: 0 0 0 0;
    }

    .content {
        margin-top: 270px;
    }
            
    .content-headings {
        font-family: 'Poppins', sans-serif;
        color: var(--brand-color);
        font-size: 24px;
        font-weight: bold;
    }
}

            
@media (max-width: 900px) {
    .fixed-header {
        top: 3.2rem;
        padding: 2px 2px 2px 2px;
        border-bottom-width: 1px;
    }

    .fixed-header img {
        width: 150px;
    }

    .fixed-header h1 {
        font-size: 18px;
        margin: 1px 0 0 0;
    }

    .content {
        margin-top: 225px;
    }
            
    .content-headings {
        font-family: 'Poppins', sans-serif;
        color: var(--brand-color);
        font-size: 15px;
    }
}            


@media (max-width: 600px) {
    .fixed-header {
        top: 3.5rem;
        padding: 0px 0px 0px 0px;
    }

    .fixed-header img {
        width: 100px;
    }

    .fixed-header h1 {
        font-size: 13px;
    }

    .content {
        margin-top: 200px;
    }
            
    .content-headings {
        font-family: 'Poppins', sans-serif;
        color: var(--brand-color);
        font-size: 12px;
    }
}
</style>

<div class="fixed-header">
    <img src="https://group.sucafina.com/themes/sucafina/assets/img/base/logo.svg">
    <h1>Geospatial Data Cleaning & Standardization Tool</h1>
</div>

<div class="content"></div>
""", unsafe_allow_html=True)
#======================================================================================================================================
# DATA LOADING AND PROCESSING COLUMN 
#======================================================================================================================================


Col1, Col2 = st.columns([1, 1])

with Col1:
    st.markdown(
        """
            <div class="content-headings">Upload Geospatial Data</div>
        """,
        unsafe_allow_html=True
    )

    final_data = pd.DataFrame()
    standardized_df = pd.DataFrame()
    base_name = pd.DataFrame()

    GEOMETRY_CANDIDATES = [
        "gps", "point", "gps_point", "gps point", "plot_gps_point", "plot gps point", 
        "Gps", "Point", "Gps_Point", "GPS POINT", "Plot_Gps_Point", "Plot Gps Point", 
        "GPS", "POINT", "GPS_POINT", "Gps Point", "PLOT_GPS_POINT", "PLOT GPS POINT", 

        "wkt", "point_wkt","point wkt", "polygon_wkt","polygon wkt", "plot_wkt", "plot wkt", 
        "Wkt", "Point_Wkt","Point Wkt", "Polygon_Wkt","Polygon Wkt", "Plot_Wkt", "Plot Wkt", 
        "WKT", "POINT_WKT","POINT WKT", "POLYGON_WKT","POLYGON WKT", "PLOT_WKT", "PLOT WKT", 

        "poly", "gps_poly", "gps poly", "plot_poly", "plot poly", "plot_gps_poly", "plot gps poly",
        "Poly", "Gps_Poly", "Gps Poly", "Plot_Poly", "Plot Poly", "Plot_Gps_Poly", "Plot Gps Poly",
        "POLY", "GPS_POLY", "GPS POLY", "PLOT_POLY", "PLOT POLY", "PLOT_GPS_POLY", "PLOT GPS POLY",

        "geom", "point_geom","point geom", "polygon_geom","polygon geom", "plot_geom", "plot geom", 
        "Geom", "Point_Geom","Point Geom", "Polygon_Geom","Polygon geom", "plot_Geom", "plot Geom", 
        "GEOM", "POINT_GEOM","POINT GEOM", "POLYGON_GEOM","POLYGON GEOM", "PLOT_GEOM", "PLOT GEOM", 

        "shape", "point_shape", "point shape", "polygon_shape", "polygon_shape", "plot_shape", "plot shape", 
        "Shape", "Point_Shape", "Point Shape", "Polygon_Shape", "Polygon_Shape", "Plot_Shape", "Plot Shape", 
        "SHAPE", "POINT_SHAPE", "POINT SHAPE", "POLYGON_SHAPE", "POLYGON SHAPE", "PLOT_SHAPE", "PLOT SHAPE", 

        "coord", "point_coord", "point coord", "polygon_coord", "polygon coord", "plot_coord", "plot coord",
        "Coord", "Point_Coord", "Point Coord", "Polygon_Coord", "Polygon Coord", "Plot_Coord", "Plot Coord",
        "COORD", "POINT_COORD", "POINT COORD", "POLYGON_COORD", "POLYGON COORD", "PLOT_COORD", "PLOT COORD",

        "latlon", "gps_latlon", "gps latlon", "plot_latlon", "plot latlon", "plot_gps_latlon", "plot gps latlon",
        "LatLon", "Gps_LatLon", "Gps LatLon", "Plot_LatLon", "Plot LatLon", "Plot_Gps_LatLon", "Plot Gps LatLon",
        "LATLON", "GPS_LATLON", "GPS LATLON", "PLOT_LATLON", "PLOT LATLON", "PLOT_GPS_LATLON", "PLOT GPS LATLON",

        "x", "y",  "lon", "lat", "longitude", "latitude", "plot_lon", "plot_lat", "plot_longitude", "plot_latitude"
        "X", "Y",  "Lon", "Lat", "Longitude", "Latitude", "Plot_Lon", "Plot_Lat", "Plot_Longitude", "Plot_Latitude"
        "X", "Y",  "LON", "LAT", "LONGITUDE", "LATITUDE", "PLOT_LON", "PLOT_LAT", "PLOT_LONGITUDE", "PLOT_LATITUDE"

        "e", "n", "east", "north", "easting", "northing", "plot_east", "plot_north", "plot_easting", "plot_northing"
        "E", "N", "East", "North", "Easting", "Northing", "Plot_East", "Plot_North", "Plot_Easting", "Plot_Northing"
        "E", "N", "EAST", "NORTH", "EASTING", "NORTHING", "PLOT_EAST", "PLOT_NORTH", "PLOT_EASTING", "PLOT_NORTHING"

        "polygon", "gps_polygon", "gps polygon", "plot_polygon", "plot polygon", "plot_gps_polygon", "plot gps polygon", 
        "Polygon", "gps_polygon", "gps polygon", "Plot_Polygon", "Plot Polygon", "Plot_Gps_Polygon", "Plot Gps Polygon", 
        "POLYGON", "GPS_POLYGON", "GPS POLYGON", "PLOT_POLYGON", "PLOT_POLYGON", "PLOT_GPS_POLYGON", "PLOT GPS POLYGON",

        "geometry", "point_geometry", "point geometry", "polygon_geometry", "polygon geometry", "plot_geometry", "plot geometry",
        "Geometry", "Point_Geometry", "Point Geometry", "Polygon_Geometry", "Polygon Geometry", "Plot_Geometry", "Plot Geometry",
        "GEOMETRY", "POINT_GEOMETRY", "POINT GEOMETRY", "POLYGON_GEOMETRY", "POLYGON GEOMETRY", "PLOT_GEOMETRY", "PLOT GEOMETRY",

        "location", "point_location", "point location", "polygon_location", "polygon location", "plot_location", "plot location",
        "Location", "Point_Location", "Point Location", "Polygon_Location", "Polygon Location", "Plot_Location", "Plot Location",
        "LOCATION", "POINT_LOCATION", "POINT LOCATION", "POLYGON_LOCATION", "POLYGON LOCATION", "PLOT_LOCATION", "PLOT LOCATION",
        
        "boundary", "point_boundary", "point boundary", "polygon_boundary", "polygon boundary", "plot_boundary", "plot boundary",
        "Boundary", "Point_boundary", "Point boundary", "Polygon_Boundary", "Polygon Boundary", "Plot_Boundary", "Plot Boundary",
        "BOUNDARY", "POINT_BOUNDARY", "POINT BOUNDARY", "POLYGON_BOUNDARY", "POLYGON BOUNDARY", "PLOT_BOUNDARY", "PLOT BOUNDARY", 

        "coordinates", "point_coordinates", "point coordinates", "polygon_coordinates", "polygon coordinates", "plot_coordinates", "plot coordinates",
        "Coordinates", "Point_Coordinates", "Point Coordinates", "Polygon_Coordinates", "Polygon Coordinates", "Plot_coordinates", "Plot coordinates",
        "COORDINATES", "POINT_COORDINATEs", "POINT COORDINATEs", "POLYGON_COORDINATEs", "POLYGON COORDINATEs", "PLOT_COORDINATEs", "PLOT COORDINATEs"   
    ]

#======================================================================================================================================
# DATA CLEANING AND GEOMETRY PROCESSING FUNCTIONS
#======================================================================================================================================
    
    def clean_geometry(value):

        if pd.isna(value) or not isinstance(value, str):
            return value

        text = value.strip()
        if not text:
            return value

        try:
            geom = None


            def strip_zvalues(coords):
                if isinstance(coords[0], (int, float)):
                    return coords[:2]
                return [strip_zvalues(c) for c in coords]

            def close_ring(coords, tol=1e-9):
                coords = list(coords)
                if len(coords) > 2:
                    x0, y0 = coords[0]
                    x1, y1 = coords[-1]
                    if abs(x0 - x1) > tol or abs(y0 - y1) > tol:
                        coords.append(coords[0])
                return coords

            def swap_coords_lon_lat(a, b):
                if abs(a) <= 90 and abs(b) <= 180:
                    return b, a
                return a, b

            def extract_xy_from_xyz(text):

                triplet_pattern = re.compile(
                    r'(-?\d+\.?\d*)\s*,\s*'
                    r'(-?\d+\.?\d*)\s*,\s*'
                    r'(-?\d+\.?\d*)'
                )

                matches = triplet_pattern.findall(text)

                coords = []
                for x, y, z in matches:
                    x = float(x)
                    y = float(y)
                    lon, lat = swap_coords_lon_lat(x, y)
                    coords.append((lon, lat))

                return coords

            def extract_xy_pairs(text):

                pair_pattern = re.compile(
                    r'(-?\d+\.?\d*)\s*[,\s]\s*'
                    r'(-?\d+\.?\d*)'
                )

                pairs = pair_pattern.findall(text)

                coords = []
                for a, b in pairs:
                    a = float(a)
                    b = float(b)
                    lon, lat = swap_coords_lon_lat(a, b)
                    coords.append((lon, lat))

                return coords

            if '"coordinates"' in text and '"type"' in text:
                geo = json.loads(text)
                geo = geo.get("geometry", geo)
                geo["coordinates"] = strip_zvalues(geo["coordinates"])
                geom = shape(geo)

            elif re.match(r'^\s*(POINT|LINESTRING|POLYGON|MULTIPOLYGON)', text, re.I):
                geom = wkt.loads(text)

            else:
                text = re.sub(r'[,\s]+$', '', text)
                xyz_coords = extract_xy_from_xyz(text)
                total_numbers = len(re.findall(r'-?\d+\.?\d*', text))

                if len(xyz_coords) >= 3 and len(xyz_coords) * 3 >= 0.6 * total_numbers:
                    coords = close_ring(xyz_coords)
                    geom = Polygon(coords)

                else:
                    coords = extract_xy_pairs(text)

                    if len(coords) == 1:
                        geom = Point(coords[0])
                    elif len(coords) >= 3:
                        coords = close_ring(coords)
                        geom = Polygon(coords)
                    else:
                        return value

            geom = transform(lambda x, y, z=None: (x, y), geom)


            if isinstance(geom, Polygon):
                geom = Polygon(
                    close_ring(geom.exterior.coords),
                    [close_ring(r.coords) for r in geom.interiors]
                )

            elif isinstance(geom, MultiPolygon):
                geom = MultiPolygon([
                    Polygon(
                        close_ring(p.exterior.coords),
                        [close_ring(r.coords) for r in p.interiors]
                    )
                    for p in geom.geoms
                ])

            if not geom.is_valid:
                geom = make_valid(geom)

            return geom.wkt

        except Exception:
            return value

#======================================================================================================================================
# CORDINATE FORMATTING FUNCTIONS
#======================================================================================================================================

    def format_coord(value):
        s = str(value)
        if '.' in s:
            integer, decimal = s.split('.')
            if len(decimal) > 6:
                return f"{round(float(s), 6):.6f}"
            elif len(decimal) < 6:
                padding = '0' * (5 - len(decimal)) + '1'
                new_decimal = decimal + padding
                return f"{integer}.{new_decimal}"
            else:
                return f"{float(s):.6f}"
        else:
            return f"{s}.000001"

    def apply_n_times(func, value, n):
        for _ in range(n):
            value = func(value)
        return value

    def process_coords(coords):
        return [(float(format_coord(x)), float(format_coord(y))) for x, y in coords]

    def process_polygon(polygon):
        exterior = process_coords(polygon.exterior.coords)
        interiors = [process_coords(ring.coords) for ring in polygon.interiors]
        return Polygon(exterior, interiors)

    def process_point(point):
        x = float(format_coord(point.x))
        y = float(format_coord(point.y))
        return Point(x, y)

    def process_wkt(wkt_string):
        try:
            geom = wkt.loads(wkt_string)

            if not geom.is_valid:
                geom = make_valid(geom)
                
            if isinstance(geom, Polygon):
                return process_polygon(geom).wkt

            elif isinstance(geom, MultiPolygon):
                return MultiPolygon(
                    [process_polygon(p) for p in geom.geoms]).wkt

            elif isinstance(geom, Point):
                return process_point(geom).wkt

            elif isinstance(geom, MultiPoint):
                return MultiPoint(
                    [process_point(p) for p in geom.geoms]).wkt
            else:
                return wkt_string

        except Exception:
            return wkt_string

#======================================================================================================================================
# CONVERTING GEOMETRY COLUMNS TO GEODATAFRAME
#======================================================================================================================================
    def normalize_text(Data):
        for col in Data.select_dtypes(include=["object"]).columns:
            Data[col] = Data[col].apply(
                lambda x: unicodedata.normalize("NFKD", str(x)).encode("ASCII", "ignore").decode("ASCII") if pd.notna(x) else x
            )
        return Data

    def convert_to_geodf(Data):


        existing_columns = [col for col in Data.columns if col.lower() in [c.lower() for c in GEOMETRY_CANDIDATES]]
        if not existing_columns:
            return Data.fillna("")

        for col in existing_columns:
            if col in Data.columns:
                Data[col] = Data[col].astype(str).apply(clean_geometry)
                Data[col] = Data[col].apply(lambda x: apply_n_times(process_wkt, x, 2))
                Data[col] = Data[col].replace({"nan": "", "NaN": ""})
            else:
                print(f"⚠ Column '{col}' not found in DataFrame, skipping...")

        polygon_cols = [c for c in existing_columns if "polygon" in c.lower()]
        point_cols   = [c for c in existing_columns if "point" in c.lower()]
        generic_cols = [c for c in existing_columns if c.lower() in ["geometry", "wkt"]]


#======================================================================================================================================
# CHOSING GEOMETRY (WKT) COLUMN BASED ON PRIORITY AND CREATING FINAL WKT COLUMN
#======================================================================================================================================

        def choose_geometry(row):
            
            
            polygon_wkt = ""
            for col in polygon_cols:
                val = row.get(col)
                if pd.notnull(val) and str(val).strip():
                    try:
                        geom = wkt.loads(val)
                        if geom.geom_type in ["Polygon", "MultiPolygon"]:
                            polygon_wkt = geom.wkt
                            break
                    except:
                        pass

            point_wkt = ""
            for col in point_cols:
                val = row.get(col)
                if pd.notnull(val) and str(val).strip():
                    try:
                        geom = wkt.loads(val)
                        if geom.geom_type == "Point":
                            point_wkt = geom.wkt
                            break
                    except:
                        pass

            generic_wkt = ""
            for col in generic_cols:
                val = row.get(col)
                if pd.notnull(val) and str(val).strip():
                    try:
                        geom = wkt.loads(val)
                        generic_wkt = geom.wkt
                        break
                    except:
                        pass

            lon_cols = [c for c in existing_columns if any(k in c.lower() for k in ["lon", "longitude", "x", "east", "easting", "plot_longitude", "plot_easting"])]
            lat_cols = [c for c in existing_columns if any(k in c.lower() for k in ["lat", "latitude", "y", "north", "northing", "plot_latitude", "plot_northing"])]

            lon = None
            for c in lon_cols:
                val = row.get(c)
                if pd.notnull(val):
                    lon = pd.to_numeric(val, errors="coerce")
                    if pd.notnull(lon):
                        break

            lat = None
            for c in lat_cols:
                val = row.get(c)
                if pd.notnull(val):
                    lat = pd.to_numeric(val, errors="coerce")
                    if pd.notnull(lat):
                        break

            coord_wkt = ""
            if pd.notnull(lon) and pd.notnull(lat):
                coord_wkt = f"POINT ({lon} {lat})"
                coord_wkt = apply_n_times(process_wkt, coord_wkt, 2)

            final_wkt = polygon_wkt if polygon_wkt else point_wkt if point_wkt else generic_wkt if generic_wkt else coord_wkt

            return pd.Series({
                "plot_gps_polygon": polygon_wkt,
                "plot_gps_point": point_wkt if point_wkt else coord_wkt,
                "plot_wkt": final_wkt
            })

        geom_df = Data.apply(choose_geometry, axis=1)
        Data = Data.drop(columns=existing_columns, errors="ignore")
        final_data = pd.concat([Data, geom_df], axis=1)
        final_data = final_data.fillna("")
        final_data.columns = final_data.columns.str.strip()
        return final_data

#======================================================================================================================================
# KML LODING FUNCTION
#======================================================================================================================================

    def load_kml(uploaded_file, ext):
        uploaded_file.seek(0)
        if ext == "kmz":
            with zipfile.ZipFile(uploaded_file) as z:
                kml_name = [f for f in z.namelist() if f.lower().endswith(".kml")][0]
                kml_bytes = z.read(kml_name)
        else:
            kml_bytes = uploaded_file.read()

        root = ET.fromstring(kml_bytes)
        ns = {"kml": "http://www.opengis.net/kml/2.2"}

        rows = []
        for placemark in root.findall(".//kml:Placemark", ns):
            geom = placemark.find(".//kml:Polygon", ns)
            if geom is None:
                geom = placemark.find(".//kml:Point", ns)
            if geom is None:
                geom = placemark.find(".//kml:LineString", ns)

            geom_wkt = ""
            if geom is not None:
                coordinates = geom.find(".//kml:coordinates", ns)
                if coordinates is not None and coordinates.text:
                    coords_text = coordinates.text.strip()
                    try:
                        geom_wkt = wkt.dumps(shape(coords_text))
                    except:
                        geom_wkt = coords_text

            row = {"plot_gps_polygon": geom_wkt if "Polygon" in geom.tag else "",
                "plot_gps_point": geom_wkt if "Point" in geom.tag else "",
                "plot_wkt": geom_wkt}

            for sd in placemark.findall(".//kml:SimpleData", ns):
                row[sd.attrib.get("name")] = sd.text
            for ed in placemark.findall(".//kml:Data", ns):
                value = ed.find("kml:value", ns)
                row[ed.attrib.get("name")] = value.text if value is not None else ""

            name = placemark.find("kml:name", ns)
            if name is not None and name.text:
                row["name"] = name.text
            desc = placemark.find("kml:description", ns)
            if desc is not None and desc.text:
                row["description"] = desc.text

            rows.append(row)

        return pd.DataFrame(rows)

#======================================================================================================================================
# LOADING DATA
#======================================================================================================================================
    def load_file(file_bytes, ext):

        ext = ext.lower()
        final_data = None

        if ext == "csv":
            raw_data = file_bytes.read()
            file_bytes.seek(0)
            encoding = chardet.detect(raw_data)["encoding"] or "utf-8"
            final_data = pd.read_csv(file_bytes, encoding=encoding)
            final_data.columns = final_data.columns.str.strip()
            final_data.columns = final_data.columns.str.replace('\u200b','')
            final_data.columns = final_data.columns.str.lower()

        elif ext in ["xls", "xlsx"]:
            header_row = st.number_input(
                "Enter the row number containing column headers",
                min_value=1,
                value=1,
                step=1
            )
            final_data = pd.read_excel(file_bytes, header=header_row - 1)

        elif ext in ["geojson", "json"]:
            gdf = gpd.read_file(file_bytes)
            final_data = pd.DataFrame(gdf)

        elif ext == "kml":
            final_data = load_kml(file_bytes, ext)

        elif ext == "zip":
            with tempfile.TemporaryDirectory() as tmpdir:

                file_bytes.seek(0)
                with zipfile.ZipFile(file_bytes) as z:
                    z.extractall(tmpdir)

                shp_files = []
                other_dfs = []

                for root, dirs, files in os.walk(tmpdir):
                    for f in files:
                        path = os.path.join(root, f)
                        e = f.split(".")[-1].lower()

                        if e == "shp":
                            shp_files.append(path)

                        elif e in ["csv", "xls", "xlsx", "geojson", "json", "kml"]:
                            with open(path, "rb") as fb:
                                df = load_file(io.BytesIO(fb.read()), e)
                                if df is not None:
                                    other_dfs.append(df)

                if shp_files:
                    gdf = gpd.read_file(shp_files[0])
                    other_dfs.append(pd.DataFrame(gdf))

                if other_dfs:
                    final_data = pd.concat(other_dfs, ignore_index=True)

        if final_data is None:
            return None

        final_data = normalize_text(final_data)
        return convert_to_geodf(final_data)


#======================================================================================================================================
# UPLOADING DATA
#======================================================================================================================================



    uploaded_file = st.file_uploader(
        "Upload CSV, Excel, GeoJSON, KML, or ZIP",
        type=["csv", "xls", "xlsx", "geojson", "kml", "zip"]
    )

    if uploaded_file:
        original_name = uploaded_file.name
        file_ext = original_name.split(".")[-1].lower()
        all_dfs = []

        if file_ext == "zip":
            with zipfile.ZipFile(uploaded_file) as zip_ref:
                for f in zip_ref.namelist():
                    ext = f.split(".")[-1].lower()
                    with zip_ref.open(f) as file_bytes:
                        final_data = load_file(file_bytes, ext)
                        if final_data is not None:
                            all_dfs.append(final_data)
            if not all_dfs:
                st.error("No valid files found in ZIP.")
                st.stop()
            final_data = pd.concat(all_dfs, ignore_index=True)
            base_name = original_name.split(".")[0]
        else:
            final_data = load_file(uploaded_file, file_ext)
            if final_data is None:
                st.error("Failed to read file.")
                st.stop()
            base_name = original_name.split(".")[0]

        st.success(f"File(s) successfully loaded ({final_data.shape[0]} rows, {final_data.shape[1]} columns)")
        st.dataframe(final_data, height=730, use_container_width=True)

#======================================================================================================================================
# STANDARDIZATION AND CERTIFICATION MAPPING
#======================================================================================================================================
with Col2:
    
    st.markdown(
        """
        <div class="content-headings">
        Standardized Geodata Schema
        </div>
        """,
        unsafe_allow_html=True
    )

    columns = [""] + list(final_data.columns)

    standard_fields = {
        "supplier_plot_id": "Supplier Plot ID*",
        "farmer_id": "Farmer ID",
        "supplier_code": "Supplier Code*",
        "plot_region": "Region",
        "plot_district": "District",
        "plot_area_ha": "Area (Ha)",
        "plot_longitude": "Longitude",
        "plot_latitude": "Latitude",
        "plot_gps_point": "GPS Point",
        "plot_gps_polygon": "GPS Polygon",
        "plot_wkt": "WKT*",
        "plot_supply_chain": "Name of Supply Chain",
        "plot_farmer_group": "Name of Farmer Group"
    }

    other_cert_fields = {
        "is_cafe_practices_certified": "CAFE PRACTICES",
        "is_rfa_utz_certified": "RA/RFA",
        "is_impact_certified": "IMPACT",
        "is_organic_certified": "ORGANIC",
        "is_4c_certified": "4C",
        "is_fairtrade_certified": "FAIRTRADE",
        "other_certification_name": "CONVENTIONAL(OTHERS)"
    }

    mapping_df = pd.DataFrame({
        "ATTRIBUTES": list(standard_fields.values()),
        "SELECT SOURCE COLUMN": "",
        "MANUAL VALUE": ""
    }, index=list(standard_fields.keys()))

    edited_mapping = st.data_editor(
        mapping_df,
        column_config={
            "ATTRIBUTES": st.column_config.Column("ATTRIBUTES", disabled=True),
            "SELECT SOURCE COLUMN": st.column_config.SelectboxColumn("SELECT SOURCE COLUMN", options=columns),
            "MANUAL VALUE": st.column_config.Column("MANUAL VALUE")
        },
        hide_index=True,
        height=500,
        use_container_width=True
    )

    cert_df = pd.DataFrame({
        "CERTIFICATIONS": list(other_cert_fields.values()),
        "SELECT SOURCE COLUMN": "",
        "TRUE/FALSE": False
    }, index=list(other_cert_fields.keys()))

    edited_cert = st.data_editor(
        cert_df,
        column_config={
            "CERTIFICATIONS": st.column_config.Column("CERTIFICATIONS", disabled=True),
            "SELECT SOURCE COLUMN": st.column_config.SelectboxColumn("SELECT SOURCE COLUMN", options=columns),
            "TRUE/FALSE": st.column_config.CheckboxColumn("TRUE/FALSE")
        },
        hide_index=True,
        use_container_width=True
    )

    is_geodata_validated = st.selectbox(
        "Is geodata validated?",
        options=[True, False],
        index=1
    )

    st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: var(--brand-color);
        color: white;
        font-size: 20px;
        font-weight: bold;
        height: 50px;
        padding: 12px 24px;
        border-radius: 8px;
        padding: 12px 24px;
        border: none;
        
    }

    div.stButton > button:first-child:hover {
        background-color: var(--brand-hover);
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)


    if st.button("Standardize Data", type="primary", use_container_width=True, disabled=not uploaded_file):

        mandatory_fields = [k for k, v in standard_fields.items() if v.endswith("*")]
        missing_fields = []

        for field in mandatory_fields:
            row = edited_mapping.loc[field]
            source = row["SELECT SOURCE COLUMN"]
            manual = str(row["MANUAL VALUE"]).strip()

            if not source and not manual:
                missing_fields.append(standard_fields[field])

        if missing_fields:
            st.error(f"Please fill mandatory fields: {', '.join(missing_fields)}")

        else:
            standardized_df = pd.DataFrame(index=final_data.index)

            for field_key, row in edited_mapping.iterrows():
                source = row["SELECT SOURCE COLUMN"]
                manual = str(row["MANUAL VALUE"]).strip()

                if manual:
                    standardized_df[field_key] = [manual] * len(final_data)

                elif source:
                    standardized_df[field_key] = final_data[source]

                else:
                    standardized_df[field_key] = ""

            if "supplier_plot_id" in standardized_df.columns:

                duplicate_ids = standardized_df["supplier_plot_id"][
                    standardized_df["supplier_plot_id"].duplicated()
                ]

                if not duplicate_ids.empty:
                    st.error("Duplicate (supplier_plot_id) values detected. Each plot ID must be unique. Please correct the duplicates before standardizing the data.")
                    st.write("Duplicate IDs:", duplicate_ids.unique())
                    st.stop()

            standardized_df["sucafina_plot_id"] = standardized_df.apply(
                lambda r: f"{r['supplier_code']}_{r['supplier_plot_id']}"
                if r["supplier_code"] and r["supplier_plot_id"]
                else "",
                axis=1
            )

            standardized_df["is_geodata_validated"] = is_geodata_validated

#======================================================================================================================================
# AREA COMPUTATAION LOGIC
#======================================================================================================================================

            if "plot_wkt" in standardized_df.columns and "plot_area_ha" in standardized_df.columns:

                def compute_area_ha(wkt_str):

                    if not wkt_str or str(wkt_str).strip() == "":
                        return None

                    try:
                        geom = wkt.loads(wkt_str)

                        if isinstance(geom, (Polygon, MultiPolygon)):

                            gdf = gpd.GeoDataFrame(
                                geometry=[geom],
                                crs="EPSG:4326"
                            )

                            projected = gdf.to_crs(epsg=3857)

                            area_m2 = projected.geometry.area.iloc[0]

                            return round(area_m2 / 10000, 3)

                        elif isinstance(geom, Point):
                            return None

                    except Exception:
                        return None

                computed_area = standardized_df["plot_wkt"].apply(compute_area_ha)

                standardized_df["plot_area_ha"] = computed_area.fillna(standardized_df["plot_area_ha"])

                point_missing_area = (
                    standardized_df["plot_wkt"].str.startswith("POINT", na=False) &
                    standardized_df["plot_area_ha"].astype(str).str.strip().eq("")
                )

                if point_missing_area.any():
                    st.error(
                        "Area (Ha) must be provided when geometry is a POINT."
                    )
                    st.stop()

#======================================================================================================================================
# CERTIFICATION MAPPING LOGIC
#======================================================================================================================================
            for field_key, row in edited_cert.iterrows():
                source = row.get("SELECT SOURCE COLUMN", None)
                fallback = row.get("TRUE/FALSE", None)

                if source and source in final_data.columns:
                    standardized_df[field_key] = final_data[source]
                elif fallback:
                    standardized_df[field_key] = True
                else:
                    standardized_df[field_key] = False

            if "plot_farmer_group" in standardized_df.columns and "is_impact_certified" in standardized_df.columns:
                standardized_df.loc[~standardized_df["is_impact_certified"], "plot_farmer_group"] = ""

            if "is_impact_certified" in standardized_df.columns and "plot_farmer_group" in standardized_df.columns:
                missing_farmer_group = standardized_df[
                    (standardized_df["is_impact_certified"] == True) &
                    (standardized_df["plot_farmer_group"].astype(str).str.strip() == "")
                ]
                if not missing_farmer_group.empty:
                    st.error(
                        "IMPACT certification requires 'Name of Farmer Group'. "
                        "Please ensure all IMPACT certified plots have a farmer group."
                    )
                    st.stop()

            st.success("Data standardized successfully.")
            st.session_state["standardized_data"] = standardized_df
    
#======================================================================================================================================
# RE-ARRANGING COLUMNS
#======================================================================================================================================
    
    desired_order = [
    "sucafina_plot_id",
    "supplier_plot_id",
    "farmer_id",
    "supplier_code",
    "plot_region",
    "plot_district",
    "plot_area_ha",
    "plot_longitude",
    "plot_latitude",
    "plot_gps_point",
    "plot_gps_polygon",
    "plot_wkt",
    "is_geodata_validated",
    "is_cafe_practices_certified",
    "is_rfa_utz_certified",
    "is_impact_certified",
    "is_organic_certified",
    "is_4c_certified",
    "is_fairtrade_certified",
    "other_certification_name",
    "plot_supply_chain",
    "plot_farmer_group"
]

standardized_df = standardized_df.reindex(columns=desired_order)


#======================================================================================================================================
# DATA DOWNLOAD OPTIONS
#======================================================================================================================================

st.markdown(
    """
    <hr style="height:2px;border:none;color:var(--brand-color);background-color:var(--brand-color);">
    """,
    unsafe_allow_html=True
)

if "standardized_df" in locals():
    st.dataframe(standardized_df, use_container_width=True)

download_format = st.selectbox("Select download format", ["CSV", "Excel", "GeoJSON", "KML"])

col1, col2 = st.columns([1, 1])

with col2:
    button_style = """
        <style>
        div.stDownloadButton > button:first-child {
            background-color: var(--brand-color);
            color: white;
            font-size: 18px;
            font-weight: bold;
            padding: 12px 24px;
            border-radius: 8px;
        }
        div.stDownloadButton > button:hover {
            background-color: var(--brand-dark);
            color: white;
        }
        </style>
    """
    st.markdown(button_style, unsafe_allow_html=True)

    if download_format == "CSV":
        st.download_button(
            "Download CSV",
            data=standardized_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{base_name}.csv",
            mime="text/csv"
        )

    elif download_format == "Excel":
        buffer = io.BytesIO()
        standardized_df.to_excel(buffer, index=False)
        st.download_button(
            "Download Excel",
            data=buffer.getvalue(),
            file_name=f"{base_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    elif download_format == "GeoJSON":
        try:
            gdf = gpd.GeoDataFrame(
                standardized_df,
                geometry=standardized_df["plot_wkt"].apply(lambda x: wkt.loads(x) if x else None),
                crs="EPSG:4326"
            )
            gdf = gdf[gdf.geometry.notnull()]
            gdf.to_file(f"{base_name}.geojson", driver="GeoJSON")
            with open(f"{base_name}.geojson", "rb") as f:
                st.download_button(
                    "Download GeoJSON",
                    data=f.read(),
                    file_name=f"{base_name}.geojson",
                    mime="application/geo+json"
                )
        except Exception as e:
            st.warning(f"GeoJSON requires valid geometries. Error: {e}")

    elif download_format == "KML":
        try:
            gdf = gpd.GeoDataFrame(
                standardized_df,
                geometry=standardized_df["plot_wkt"].apply(lambda x: wkt.loads(x) if x else None),
                crs="EPSG:4326"
            )
            gdf = gdf[gdf.geometry.notnull()]
            gdf.to_file(f"{base_name}.kml", driver="KML")
            with open(f"{base_name}.kml", "rb") as f:
                st.download_button(
                    "Download KML",
                    data=f.read(),
                    file_name=f"{base_name}.kml",
                    mime="application/vnd.google-earth.kml+xml"
                )
        except Exception as e:
            st.warning(f"KML requires valid geometries. Error: {e}")

st.markdown(
    """
    <hr style="height:2px;border:none;color:var(--brand-color);background-color:var(--brand-color);">
    """,
    unsafe_allow_html=True
)
