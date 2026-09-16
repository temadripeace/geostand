import io
import re
import json
import zipfile
import chardet
import tempfile
import unicodedata
import pandas as pd
import streamlit as st
import geopandas as gpd
from shapely import wkt
from pyproj import Geod
import xml.etree.ElementTree as ET
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
        font-size:12px;
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
    <li>Computes plot area (ha) for Polygons & Multipolygons.</li>
    <li>Cleans small spikes and self-intersections.</li>
    <li>Maps data fields to Sucafina's standardised Geodata Schema.</li>
    <li>Exports standardised data to CSV, Excel, KML, or GeoJSON formats.</li>
    </ul>

    <b> REQUIRED GEOMETRY COLUMN NAMES</b>
    <li><b>Longitude / Latitude (Separate Columns):</b>
    lon, lat, Lon, Lat, LON, LAT, longitude, latitude, Longitude, Latitude, LONGITUDE, LATITUDE<br></li>

    <li><b>Single Column Points:</b>
    point, Point, POINT, gps_point, GPS_POINT, plot_gps_point, PLOT_GPS_POINT, geom, GEOM, geometry, GEOMETRY, wkt, WKT<br></li>

    <li><b>Polygons/Multipolygons:</b>
    polygon, Polygon, POLYGON, gps_polygon, GPS_POLYGON, plot_gps_polygon, PLOT_GPS_POLYGON, geom, GEOM, geometry, GEOMETRY, wkt, WKT</li>

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

    final_data = pd.DataFrame()
    standardized_df = pd.DataFrame()
    base_name = pd.DataFrame()

    world = pd.read_csv('country_bounding_boxes.csv')

    st.markdown(
            """
                <div class="content-headings">Select Coffee Origin (Country) </div>
            """,
            unsafe_allow_html=True
        )

    country_list = sorted(world["country"].dropna().unique())
    
    country = st.selectbox(
        "Please select an Origin Country",
        country_list,
        index=None,
        placeholder="Search a country"
    )

    if not country:
        st.stop()

    
    if country:
        filtered = world[world["country"] == country]

        if not filtered.empty:
            selected = filtered.iloc[0]

            minx, miny = selected["min_lon"], selected["min_lat"]
            maxx, maxy = selected["max_lon"], selected["max_lat"]

            bounding_box = (miny, maxy, minx, maxx)
        else:
            bounding_box = None
    st.markdown(
            f"""
            <p>
            <b>Bounding Box:</b>
            Min Lon: <span style="color:red;">{minx}</span>, 
            Min Lat: <span style="color:red;">{miny}</span> | 
            Max Lon: <span style="color:red;">{maxx}</span>, 
            Max Lat: <span style="color:red;">{maxy}</span>
            </p>
            """,
            unsafe_allow_html=True
        )
          
#======================================================================================================================================
# DATA LOADING AND PROCESSING COLUMN 
#======================================================================================================================================


    st.markdown(
        """
            <div class="content-headings">Upload Geospatial Data</div>
        """,
        unsafe_allow_html=True
    )

    def normalize(col):
        col = str(col).strip().lower()
        col = unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('ascii')
        col = col.replace(" ", "_")
        return col

    GEOMETRY_CANDIDATES = [
        "gps", "point",  "punto", "puntos", "gps_point", "plot_gps_point",

        "wkt", "point_wkt", "polygon_wkt", "plot_wkt",

        "poly", "polygon", "poligono", "poligonos"
        "gps_poly", "plot_poly", "plot_gps_poly",
        "polygon_points", "polygon_point",

        "geom", "point_geom", "polygon_geom", "plot_geom",

        "shape", "point_shape", "polygon_shape", "plot_shape",

        "coord", "point_coord", "polygon_coord", "plot_coord",

        "latlon", "gps_latlon", "plot_latlon", "plot_gps_latlon",

        "x", "y", "lon", "lat", "longitude", "latitude",
        "plot_lon", "plot_lat", "plot_longitude", "plot_latitude",

        "e", "n", "east", "north", "easting", "northing",
        "plot_east", "plot_north", "plot_easting", "plot_northing",

        "polygon", "gps_polygon", "plot_polygon", "plot_gps_polygon",

        "geometry", "point_geometry", "polygon_geometry", "plot_geometry",

        "location", "point_location", "polygon_location", "plot_location",

        "boundary", "point_boundary", "polygon_boundary", "plot_boundary",

        "coordinates", "point_coordinates", "polygon_coordinates", "plot_coordinates"
    ]

    def find_geom_columns(df):
        normalized_candidates = [normalize(c) for c in GEOMETRY_CANDIDATES]

        geom_columns = [
            col for col in df.columns
            if any(candidate in normalize(col) for candidate in normalized_candidates)
        ]

        return geom_columns

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

            def swap_coords_lon_lat(lon, lat, bounds):
                min_lat, max_lat, min_lon, max_lon = bounds

                lon_in_lat_range = min_lat <= lon <= max_lat
                lon_in_lon_range = min_lon <= lon <= max_lon

                lat_in_lat_range = min_lat <= lat <= max_lat
                lat_in_lon_range = min_lon <= lat <= max_lon

                if lon_in_lon_range and lat_in_lat_range:
                    return (lon, lat)

                if lon_in_lat_range and lat_in_lon_range:
                    return (lat, lon)

                return (lon, lat)

            def fix_geometry(geom, bounds):

                if isinstance(geom, Point):
                    lon, lat = geom.x, geom.y
                    lon, lat = swap_coords_lon_lat(lon, lat, bounds)
                    return Point(lon, lat)

                if isinstance(geom, Polygon):
                    exterior = [swap_coords_lon_lat(lon, lat, bounds) for lon, lat in geom.exterior.coords]
                    interiors = [
                        [swap_coords_lon_lat(lon, lat, bounds) for lon, lat in ring.coords]
                        for ring in geom.interiors
                    ]
                    return Polygon(close_ring(exterior), [close_ring(r) for r in interiors])

                if isinstance(geom, MultiPolygon):
                    return MultiPolygon([fix_geometry(p, bounds) for p in geom])

                return geom

            def extract_xy_from_xyz(text):
                triplet_pattern = re.compile(
                    r'(-?\d+\.?\d*)\s*,\s*'
                    r'(-?\d+\.?\d*)\s*,\s*'
                    r'(-?\d+\.?\d*)'
                )
                matches = triplet_pattern.findall(text)

                coords = [(float(x), float(y)) for x, y, z in matches]
                return coords

            def extract_xy_pairs(text):
                pair_pattern = re.compile(
                    r'(-?\d+\.?\d*)\s*[,\s]\s*'
                    r'(-?\d+\.?\d*)'
                )
                pairs = pair_pattern.findall(text)

                coords = [(float(a), float(b)) for a, b in pairs]
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
                        geom = Polygon(close_ring(coords))
                    else:
                        return value

            geom = fix_geometry(geom, bounding_box)

            geom = transform(lambda x, y, z=None: (x, y), geom)

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
        return [(float(format_coord(lon)), float(format_coord(lat))) for lon, lat in coords]

    def process_polygon(polygon):
        exterior = process_coords(polygon.exterior.coords)
        interiors = [process_coords(ring.coords) for ring in polygon.interiors]
        return Polygon(exterior, interiors)

    def process_point(point):
        lon = float(format_coord(point.x))
        lat = float(format_coord(point.y))
        return Point(lon, lat)

    def process_wkt(wkt_string):
        try:
            geom = wkt.loads(wkt_string)
                
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
        geometry_cols = [c for c in existing_columns if c.lower() in ["geometry", "wkt"]]


#======================================================================================================================================
# CHOSING GEOMETRY (WKT) COLUMN BASED ON PRIORITY AND CREATING FINAL WKT COLUMN
#======================================================================================================================================

        def choose_geometry(row):
            
            polygon = ""
            for col in polygon_cols:
                val = row.get(col)
                if pd.notnull(val) and str(val).strip():
                    try:
                        geom = wkt.loads(val)
                        if geom.geom_type in ["Polygon", "MultiPolygon"]:
                            polygon = geom.wkt
                            break
                    except:
                        pass

            point = ""
            for col in point_cols:
                val = row.get(col)
                if pd.notnull(val) and str(val).strip():
                    try:
                        geom = wkt.loads(val)
                        if geom.geom_type == "Point":
                            point = geom.wkt
                            break
                    except:
                        pass

            geometry = ""
            for col in geometry_cols:
                val = row.get(col)
                if pd.notnull(val) and str(val).strip():
                    try:
                        geom = wkt.loads(val)
                        geometry = geom.wkt
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

            final_wkt = polygon if polygon else point if point else geometry if geometry else coord_wkt

            return pd.Series({
                "plot_gps_polygon": polygon,
                "plot_gps_point": point if point else coord_wkt,
                "plot_wkt": final_wkt
            })

        geom_df = Data.apply(choose_geometry, axis=1)
        Data = Data.drop(columns=existing_columns, errors="ignore")
        final_data = pd.concat([Data, geom_df], axis=1)
        final_data = final_data.fillna("")
        final_data.columns = final_data.columns.str.strip()
        final_data.columns = final_data.columns.str.replace('\u200b','')
        final_data.columns = final_data.columns.str.lower()

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
# GeoJSON LODING FUNCTION
#======================================================================================================================================

    def load_geojson(uploaded_file, ext):
        uploaded_file.seek(0)

        if ext == "zip":
            with zipfile.ZipFile(uploaded_file) as z:
                geojson_files = [f for f in z.namelist() if f.lower().endswith((".geojson", ".json"))]
                if not geojson_files:
                    return None
                dfs = []
                for fname in geojson_files:
                    file_bytes = z.read(fname)
                    try:
                        file_str = file_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        file_str = file_bytes.decode("latin-1")
                    data = json.loads(file_str)
                    features = data.get("features", [])
                    rows = []
                    for feature in features:
                        geom = feature.get("geometry")
                        props = feature.get("properties") or {}
                        geom_wkt = ""
                        geom_type = ""
                        if geom:
                            try:
                                shapely_geom = shape(geom)
                                geom_wkt = wkt.dumps(shapely_geom)
                                geom_type = shapely_geom.geom_type
                            except:
                                geom_wkt = ""
                        row = {
                            "plot_gps_polygon": geom_wkt if geom_type in ["Polygon", "MultiPolygon"] else "",
                            "plot_gps_point": geom_wkt if geom_type == "Point" else "",
                            "plot_wkt": geom_wkt
                        }
                        for k, v in props.items():
                            row[k] = v
                        extra_keys = [k for k in feature.keys() if k not in ["type", "geometry", "properties"]]
                        for key in extra_keys:
                            row[key] = feature.get(key)
                        rows.append(row)
                    dfs.append(pd.DataFrame(rows))
                if not dfs:
                    return None
                return pd.concat(dfs, ignore_index=True, sort=False)
        else:
            file_bytes = uploaded_file.read()
            try:
                file_str = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                file_str = file_bytes.decode("latin-1")
            data = json.loads(file_str)
            features = data.get("features", [])
            rows = []
            for feature in features:
                geom = feature.get("geometry")
                props = feature.get("properties") or {}
                geom_wkt = ""
                geom_type = ""
                if geom:
                    try:
                        shapely_geom = shape(geom)
                        geom_wkt = wkt.dumps(shapely_geom)
                        geom_type = shapely_geom.geom_type
                    except:
                        geom_wkt = ""
                row = {
                    "plot_gps_polygon": geom_wkt if geom_type in ["Polygon", "MultiPolygon"] else "",
                    "plot_gps_point": geom_wkt if geom_type == "Point" else "",
                    "plot_wkt": geom_wkt
                }
                for k, v in props.items():
                    row[k] = v
                extra_keys = [k for k in feature.keys() if k not in ["type", "geometry", "properties"]]
                for key in extra_keys:
                    row[key] = feature.get(key)
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


        elif ext in ["xls", "xlsx"]:
            header_row = st.number_input(
                "Enter the row number containing column headers",
                min_value=1,
                value=1,
                step=1
            )
            final_data = pd.read_excel(file_bytes, header=header_row - 1)

        elif ext == "kml":
            final_data = load_kml(file_bytes, ext)


        elif ext in ["geojson", "json"]:
            final_data = load_geojson(file_bytes, ext)

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
# DATA DOWNLOAD OPTIONS
#======================================================================================================================================
        download_format = st.selectbox(
            "Select download format",
            ["CSV", "Excel", "GeoJSON", "KML"],
            key="download_format"
        )

        if download_format == "CSV":

            csv_data = final_data.to_csv(index=False).encode("utf-8")

            st.download_button(
                "Download CSV",
                data=csv_data,
                file_name=f"{base_name}.csv",
                mime="text/csv",
                key="download_csv",
                use_container_width=True
            )

        elif download_format == "Excel":

            buffer = io.BytesIO()

            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                final_data.to_excel(writer, index=False)

            st.download_button(
                "Download Excel",
                data=buffer.getvalue(),
                file_name=f"{base_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel",
                use_container_width=True
            )

        elif download_format == "GeoJSON":

            if "plot_wkt" not in final_data.columns:
                st.error("Column 'plot_wkt' is required for GeoJSON export.")
            else:
                try:
                    gdf = gpd.GeoDataFrame(
                        final_data.copy(),
                        geometry=final_data["plot_wkt"].apply(
                            lambda x: wkt.loads(x) if pd.notna(x) and str(x).strip() else None
                        ),
                        crs="EPSG:4326"
                    )

                    gdf = gdf[gdf.geometry.notnull()]

                    geojson_data = gdf.to_json().encode("utf-8")

                    st.download_button(
                        "Download GeoJSON",
                        data=geojson_data,
                        file_name=f"{base_name}.geojson",
                        mime="application/geo+json",
                        key="download_geojson",
                        use_container_width=True
                    )

                except Exception as e:
                    st.error(f"GeoJSON export failed: {e}")

        elif download_format == "KML":

            if "plot_wkt" not in final_data.columns:
                st.error("Column 'plot_wkt' is required for KML export.")
            else:
                try:
                    gdf = gpd.GeoDataFrame(
                        final_data.copy(),
                        geometry=final_data["plot_wkt"].apply(
                            lambda x: wkt.loads(x) if pd.notna(x) and str(x).strip() else None
                        ),
                        crs="EPSG:4326"
                    )

                    gdf = gdf[gdf.geometry.notnull()]

                    with tempfile.NamedTemporaryFile(suffix=".kml") as tmp:
                        gdf.to_file(tmp.name, driver="KML")

                        with open(tmp.name, "rb") as f:
                            kml_data = f.read()

                    st.download_button(
                        "Download KML",
                        data=kml_data,
                        file_name=f"{base_name}.kml",
                        mime="application/vnd.google-earth.kml+xml",
                        key="download_kml",
                        use_container_width=True
                    )

                except Exception as e:
                    st.error(f"KML export failed: {e}")

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
        "plot_wkt": "Geometry*",
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


#======================================================================================================================================
# STANDARDIZATION BUTTON AND LOGIC
#======================================================================================================================================
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
# FLAGGING DOUPLICATE PLOT IDs/CREATING SUCAFINA_PLOT_ID IF SUPPLIER PLOT ID ARE VALID AND EXIST IN THE DATASET
#======================================================================================================================================

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

                duplicate_mask = standardized_df["supplier_plot_id"].duplicated(keep=False)
                duplicate_rows = standardized_df[duplicate_mask]

                if not duplicate_rows.empty:
                    duplicate_ids = duplicate_rows["supplier_plot_id"].unique()

                    st.error("Duplicate or missing (supplier_plot_id) values detected: Please ensure that each plot ID is unique and not empty")
                    st.dataframe(duplicate_rows)
                    st.stop()

            if "plot_wkt" in standardized_df.columns:

                duplicate_geom_mask = standardized_df["plot_wkt"].duplicated(keep=False)
                duplicate_geom_rows = standardized_df[duplicate_geom_mask]

                if not duplicate_geom_rows.empty:
                    duplicate_geom = duplicate_geom_rows["plot_wkt"].unique()

                    st.error("Duplicate plot GEOMETRY values detected: Please ensure that each plot GEOMETRY value is unique and not empty")
                    st.dataframe(duplicate_geom_rows)
                    st.stop()


            standardized_df["sucafina_plot_id"] = standardized_df.apply(
                lambda r: f"{r['supplier_code']}_{r['supplier_plot_id']}"
                if r["supplier_code"] and r["supplier_plot_id"]
                else "",
                axis=1
            )

            standardized_df["is_geodata_validated"] = is_geodata_validated

#======================================================================================================================================
# AREA COMPUTATAION LOGIC FOR PLOYGONS /FLAGS FOR POINTS MISSING AREA OR WITH AREA GREATER THAN 4 HA
#======================================================================================================================================

            geod = Geod(ellps="WGS84")

            def compute_area_ha(wkt_str):
                if not wkt_str or str(wkt_str).strip() == "":
                    return None

                try:
                    geom = wkt.loads(wkt_str)

                    if isinstance(geom, Polygon):
                        area, _ = geod.geometry_area_perimeter(geom)
                        return round(abs(area) / 10000, 3)

                    elif isinstance(geom, MultiPolygon):
                        area = sum(abs(geod.geometry_area_perimeter(poly)[0]) for poly in geom.geoms)
                        return round(area / 10000, 3)

                    elif isinstance(geom, Point):
                        return None

                except Exception:
                    return None

            computed_area = standardized_df["plot_wkt"].apply(compute_area_ha)
            standardized_df["plot_area_ha"] = computed_area.fillna(standardized_df["plot_area_ha"])

            point_missing_area = (
                standardized_df["plot_wkt"].str.startswith("POINT", na=False) &
                (standardized_df["plot_area_ha"].astype(str).str.strip() == "")
            )

            if point_missing_area.any():
                st.error("Missing Area for Plot(s): Please provide the Reported Area (Ha) for all plots mapped as POINT geometries")
                st.write(standardized_df[point_missing_area])
                st.stop()

            point_large_area = (
                standardized_df["plot_wkt"].str.startswith("POINT", na=False) &
                (pd.to_numeric(standardized_df["plot_area_ha"], errors="coerce") > 4)
            )

            if point_large_area.any():
                st.error("POINT Geometry Plot(s) with an area greater than 4 Ha detected: Please verify the reported area or remap these plots as POLYGON geometries.")
                st.write(standardized_df[point_large_area])
                st.stop()

#======================================================================================================================================
# CERTIFICATION MAPPING LOGIC
#======================================================================================================================================
            def to_bool(value):
                if pd.isna(value):
                    return False
                
                value = str(value).strip().lower()
                
                if value in ["true", "yes", "1"]:
                    return True
                elif value in ["false", "no", "0"]:
                    return False
                else:
                    return False
                
            for field_key, row in edited_cert.iterrows():
                source = row.get("SELECT SOURCE COLUMN", None)
                fallback = row.get("TRUE/FALSE", None)

                if source and source in final_data.columns:
                    standardized_df[field_key] = final_data[source].apply(to_bool)
                else:
                    standardized_df[field_key] = to_bool(fallback)

            if "plot_farmer_group" in standardized_df.columns and "is_impact_certified" in standardized_df.columns:
                standardized_df.loc[~standardized_df["is_impact_certified"], "plot_farmer_group"] = ""

            if "is_impact_certified" in standardized_df.columns and "plot_farmer_group" in standardized_df.columns:
                missing_farmer_group = standardized_df[
                    (standardized_df["is_impact_certified"] == True) &
                    (standardized_df["plot_farmer_group"].astype(str).str.strip() == "")
                ]
                if not missing_farmer_group.empty:
                    st.error(
                        "All IMPACT-Certified plots must have a ‘Farmer Group Name’: Please provide this information before proceeding."
                    )
                    st.stop()

            st.success("Data standardized successfully.")
            st.session_state["standardized_data"] = standardized_df
    

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
