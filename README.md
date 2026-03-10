# Geospatial Data Cleaning & Standardization Tool
This tool performs geospatial data cleaning and standardisation, enabling seamless integration with Meridia and other geospatial platforms. It supports multiple file formats, including CSV, GeoJSON, KML, Excel, and ZIP archives, as well as various character encodings such as UTF-8, Latin1, and Windows-1252, ensuring special characters are handled correctly during data processing.

# Key Features 

Cleans special characters and prevents encoding issues.
Converts geometry columns into valid WKT format.
Closes POLYGON and MULTIPOLYGON rings.
Arranges coordinates in Longitude/Latitude format.
Removes Z-values to keep geometries in 2D.
Formats coordinates to six decimal places.
Cleans small spikes and self-intersections.
Maps data fields to Sucafina's Standardised Geodata Schema.
Exports standardised data to CSV, Excel, KML, or GeoJSON formats.
