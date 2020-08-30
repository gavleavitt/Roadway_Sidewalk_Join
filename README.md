# Roadway Sidewalk Join
ArcPy script to join sidewalk information stored in a CSV to roadway centerlines. 

Sidewalk information was stored within a CSV as sidewalk width between two cross streets such as: "Main St" in column 1, and "2nd St to 5th St" in column 2, with column 3 containing width. Roadway centerlines were stored as named line segments between intersections.

Since one sidewalk width entry can span multiple intersections, this script was built apply width information to just those segments between the cross streets.

First all segments with the street name in column 1 were selected and a single line was generated used all these segments,  then the 2 streets from column 2 were selected where they intersected the primary street from column 1. The primary street would then be split at these two intersections, returning only the section between the two cross streets. This split line would then be used to select all the roadway centerline segments which perfectly matched its geometry, selecting just the primary road segments between the two cross streets, possibly extending past many intersections. 

Finally a update cursor was then used to update the sidewalk diameters on the roadway centerlines table for these primary street segments.

