# Dataset description.

This dataset adresses the task of detecting, from an airplane point of view, the runway for landing. 
The runway images are found in ./images. For each image, the associated label (runway position) and its metadata
can be found in the csv file in the same folder of this readme (dataset_name.csv). Most of the images are simulated
images from Google Earth Studio, provided with proper attributions.

For each image, the label is the position of each corner of the runway in the image. Hence, it can be used in both 
detection and segmentation approaches.

### CSV file
The csv file contains one header line, with each of its 25 columns name. Separator is ";".
If a metadata value was missing, the cell is left empty.

Columns names and description :

- image: path to the image relative to the csv. Ex : images/image_1.png. 
- height : height, in pixel, of the image
- width : width, in pixel, of the image
- type : it currently can take two different values, "earth_studio" or "real". 
  - "real" means the image was extracted from a real video from an airplane, often taken from inside the plane cockpit 
  (we might see parts of the cockpit in the image).
  - "earth_studio" means the image was generated from Google Earth Studio.
- original_dataset : the name of the dataset the image was taken from. 
- scenario : id of the acquisition scenario. 1 scenario == 1 plane approach. The id of the form AIRPORT_RUNWAY_NBIMAGES,
where AIRPORT is the ICAO airport code, RUNWAY the runway number and NBIMAGES the number of image originally generated
during the scenario. Invalid images (when the runway is not fully visible in the image) were removed after generation, 
so the real number of image of the scenario found in ./image can be lower than NBIMAGES.
- airport : ICAO code of the airport
- runway : runway id. May contains letters (L/C/R for Left/Center/Right).
- time_to_landing : duration in seconds before reaching the landing target
- weather : weather during landing. Currently either empty or "rain"
- night : if the image was taken during the night. This field was not provided for simulated image, as Google Earth Studio
"night" images are not generated from night-time views, and as such were really different from real night images. If needed,
you can use the field "time" to compute night for simulated image.
- time : when the image was taken or generated. Its format is "yyyy-MM-dd HH:mm:ss"
- slant_distance : the 3D Cartesian distance from the aircraft position to the runway reference point.
- along_track_distance : distance between the aircraft and the runway reference point projected on the extended runway 
centerline
- height_above_runway : distance along the Z axis, or difference between the aircrafts true altitude and the runway elevation
- lateral_path_angle : angle in the horizontal plane formed between the runways extended centerline and the line segment 
drawn from the lateral path angle reference point to the aircrafts position.
- vertical_path_angle : angle in the vertical plane formed between the local horizontal plane and the line segment drawn from 
the vertical path angle reference point to the aircrafts position.
- yaw : Yaw angle in degree, between -180 and 180. 0 is South, 180 North. Yaw - (Runway_number * 10) allows to get the 
yaw relative to the runway. 
- pitch : Pitch angle in degree, clockwise. 90 means horizontal.
- roll : Roll angle in degree, counterclockwise. 0 means horizontal.
- x_A : x coordinate of corner A, in pixel. Corners A,B,C,D are named depending on their order in the image if you read it pixel per pixel 
line by line. I.e sorted first per ascending y value, then per ascending x value if y is equal.
- y_A : y coordinate of corner A, in pixel. 
- x_B : x coordinate of corner B, in pixel.
- y_B : y coordinate of corner B, in pixel.
- x_C : x coordinate of corner C, in pixel.
- y_C : y coordinate of corner C, in pixel.
- x_D : x coordinate of corner D, in pixel.
- y_D : y coordinate of corner D, in pixel.