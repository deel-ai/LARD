import math
import numpy as np
import cv2

from src.ges.geo_utils import sin, cos, fit_3d_plane_from_points, projection_3d_point_on_plane, \
    closest_point_on_line, find_angle_between_vectors, \
    get_distance_between_2_points, find_center, adjust_index, \
    adjust_point_projection

from skspatial.objects import Point



class GESCamera(object):

    def __init__(self, frame_shape, frame_data):
        self.frame_data = frame_data

        self.width = frame_shape[1]
        self.height = frame_shape[0]

        self.fov_vertical = None
        self.fov_horizontal = None
        self.intrinsics = None
        self.extrinsics = None
        self.position = frame_data['position']
        self.rotation = frame_data['rotation']
        self.rotation_matrix = None
        self.coordinate = frame_data['coordinate']

        self.runway_plane = None
        self.projected_position_on_runway_plane = None
        self.projected_position_along_track = None

        self.along_track_distance = 0
        self.cross_track_distance = 0
        self.height_above_runway = 0
        self.slant_distance = 0
        self.lateral_path_angle = 0
        self.lateral_path_angle_reference_point = [0,0,0]
        self.vertical_path_angle = 0
        self.vertical_path_angle_reference_point = [0, 0, 0]
        self.bbox = None
        self.runway_corners = []

        self.pitch = None
        self.roll = None
        self.yaw = None

    @staticmethod
    def compute_rotation_matrix(rX, rY, rZ):
        """
        Compute the rotation matrix 3X3 based on three angle rotations for each axis.
        :param rX: Rotation angle around x-axis [in degrees]
        :param rY: Rotation angle around y-axis [in degrees]
        :param rZ: Rotation angle around z-axis [in degrees]
        :return:  Rotation matrix R
        """
        Rx = np.matrix([[1, 0, 0],
                        [0, cos(rX), -sin(rX)],
                        [0, sin(rX), cos(rX)]])

        Ry = np.matrix([[cos(rY), 0, sin(rY)],
                        [0, 1, 0],
                        [-sin(rY), 0, cos(rY)]])

        Rz = np.matrix([[cos(rZ), -sin(rZ), 0],
                        [sin(rZ), cos(rZ), 0],
                        [0, 0, 1]])
        R = Rx * Ry * Rz

        return R.transpose()


    def compute_intrinsics_matrix(self):
        
        """  
        compute the intrinsics matrix from the camera
        
        """

        # K Matrix or Intrinsic matrix.
        self.fov_vertical = self.frame_data['fovVertical']
        self.fov_horizontal = math.degrees(
            2 * math.atan(self.width * math.tan(math.radians(self.fov_vertical / 2)) / self.height))

        fy = self.height / (2 * math.tan(math.radians(self.fov_vertical / 2)))
        fx = self.width / (2 * math.tan(math.radians(self.fov_horizontal / 2)))

        cy = self.height / 2
        cx = self.width / 2
        self.intrinsics = np.matrix([[fx, 0, cx],
                                     [0, fy, cy],
                                     [0, 0, 1]])


    def compute_extrinsics_matrix(self):
        
        """ 
        compute extrinsics matrix
        
        """

        rX = self.rotation['x']
        rY = self.rotation['y']
        rZ = self.rotation['z']

        self.rotation_matrix = self.compute_rotation_matrix(rX, rY, rZ)

        # Position Camera 3D
        camera_position = np.matrix([[self.position['x']],
                               [self.position['y']],
                               [self.position['z']]])
        # Translation Vector
        t = -self.rotation_matrix * camera_position
        self.extrinsics = np.matrix([[self.rotation_matrix[0, 0], self.rotation_matrix[0, 1], self.rotation_matrix[0, 2], t[0, 0]],
                                     [self.rotation_matrix[1, 0], self.rotation_matrix[1, 1], self.rotation_matrix[1, 2], t[1, 0]],
                                     [self.rotation_matrix[2, 0], self.rotation_matrix[2, 1], self.rotation_matrix[2, 2], t[2, 0]]])

    @staticmethod
    def projection3d_2d(intrinsics, extrinsics, points_3d):
        """  
        compute the projection of points in the image coordonate system
        using intrinsics and extrinsincs matrix from the camera taking the picture
        
        """
        points_2d = []
        points_3d_camera = []
        adjust_flag = False
        for point_3d in points_3d:
            Xw = np.matrix([[point_3d[0]],
                            [point_3d[1]],
                            [point_3d[2]],
                            [1]])
            Xw_c = extrinsics*Xw
            points_3d_camera.append(Xw_c)
            if Xw_c[2] < 1:
                adjust_flag = True
        if adjust_flag is True:
            points_3d_camera = GESCamera.adjust_point_position(points_3d_camera)

        for point_3d in points_3d_camera:
            Xw_c =point_3d
            u = intrinsics * Xw_c
            points_2d.append(np.array([int(u[0][0] / u[2][0]), int(u[1][0] / u[2][0])], dtype=int))

        return points_2d


    @staticmethod
    def adjust_point_position(points_3d_camera):

        if len(points_3d_camera) == 4:
            #Points C - A
            points_3d_camera[3], points_3d_camera[0] = adjust_point_projection([points_3d_camera[3], points_3d_camera[0]]
                                                             , z=10)
            # Points D - B
            points_3d_camera[2], points_3d_camera[1] = adjust_point_projection([points_3d_camera[2], points_3d_camera[1]]
                                                                               , z=10)
        elif len(points_3d_camera) == 2:
            points_3d_camera = adjust_point_projection(points_3d_camera, z=10)
        return points_3d_camera


    @staticmethod
    def image_boundary(height, width, points_2d):
        crop_images = []

        if len(points_2d) == 4:
            #Points D - A
            new_points =  adjust_index([points_2d[3], points_2d[0]], height, width)
            if new_points[0] is not None:
                crop_images.append(new_points[0])
            if new_points[1] is not None:
                crop_images.append(new_points[1])

            #Points A - B
            new_points = adjust_index([points_2d[0], points_2d[1]], height, width)
            if new_points[0] is not None:
                crop_images.append(new_points[0])
            if new_points[1] is not None:
                crop_images.append(new_points[1])

            # Points C - B
            new_points = adjust_index([points_2d[1], points_2d[2]], height, width)
            if new_points[0] is not None:
                crop_images.append(new_points[0])
            if new_points[1] is not None:
                crop_images.append(new_points[1])

            #Points C - D
            new_points= adjust_index([points_2d[2], points_2d[3]], height, width)
            if new_points[0] is not None:
                crop_images.append(new_points[0])
            if new_points[1] is not None:
                crop_images.append(new_points[1])

        elif len(points_2d) == 2:
            new_points = adjust_index(points_2d, height, width)
            if new_points[0] is not None:
                crop_images.append(new_points[0])
            if new_points[1] is not None:
                crop_images.append(new_points[1])
        return crop_images

    @staticmethod
    def display_points(frame, points_2d = None):
        for points in points_2d:
            cv2.circle(frame, (int(points[0]), int(points[1])), 15, [0, 0, 255], thickness=7)

        cv2.namedWindow('Frame', 0)
        cv2.imshow('Frame', frame)
        cv2.waitKey(0)

        return frame

    def compute_runway_corners_projection(self, runways_database, airport, runway, delta_x=0, delta_y=0):
        runway_points = runways_database[airport][runway]

        runway_corners_3d = [list(runway_points['A']['position'].values()),
                          list(runway_points['B']['position'].values()),
                          list(runway_points['C']['position'].values()),
                          list(runway_points['D']['position'].values())]

        #noralized vectors
        vectorAB = (np.array(runway_corners_3d[0]) - np.array(runway_corners_3d[1])) / np.linalg.norm(np.array(runway_corners_3d[0]) - np.array(runway_corners_3d[1]))
        vectorDC = (np.array(runway_corners_3d[3]) - np.array(runway_corners_3d[2])) / np.linalg.norm(np.array(runway_corners_3d[3]) - np.array(runway_corners_3d[2]))
        vectorAD = (np.array(runway_corners_3d[0]) - np.array(runway_corners_3d[3])) / np.linalg.norm(np.array(runway_corners_3d[0]) - np.array(runway_corners_3d[3]))
        vectorBC = (np.array(runway_corners_3d[1]) - np.array(runway_corners_3d[2])) / np.linalg.norm(np.array(runway_corners_3d[1]) - np.array(runway_corners_3d[2]))
        #We add deltax and deltay to the corners (in order to have a margin)
        runway_corners_3d[0] = np.array(runway_corners_3d[0])  + vectorAB * delta_x + vectorAD * delta_y
        runway_corners_3d[1] = np.array(runway_corners_3d[1]) - vectorAB * delta_x + vectorBC * delta_y
        runway_corners_3d[2] = np.array(runway_corners_3d[2])  - vectorDC * delta_x - vectorBC * delta_y
        runway_corners_3d[3] = np.array(runway_corners_3d[3]) + vectorDC * delta_x - vectorAD * delta_y

        return GESCamera.projection3d_2d(self.intrinsics, self.extrinsics, runway_corners_3d)

    def compute_runway_axis_projection(self, runways_database, airport, runway, delta=0):
        runway_points = runways_database[airport][runway]

        _, ltp = find_center([list(runway_points['C']['position'].values()), list(runway_points['D']['position'].values())])
        _, fpap = find_center([list(runway_points['A']['position'].values()), list(runway_points['B']['position'].values())])

        runway_axis_3d = [ltp, fpap]

        vector = (np.array(runway_axis_3d[0]) - np.array(runway_axis_3d[1])) / np.linalg.norm(np.array(runway_axis_3d[0]) - np.array(runway_axis_3d[1]))

        runway_axis_3d[0] = np.array(runway_axis_3d[0])  + vector * delta
        runway_axis_3d[1] = np.array(runway_axis_3d[1]) - vector * delta

        return GESCamera.projection3d_2d(self.intrinsics, self.extrinsics, runway_axis_3d)


    def display_runway(self, frame, runways_database, airport, name, bbox=True,
                       centerline=True, contours=True, sidelines=True, corners=True,
                       delta_x=0, delta_y=0):

        runway_corners_2d = self.compute_runway_corners_projection(runways_database, airport, name, delta_x, delta_y)
        runway_axis_2d = self.compute_runway_axis_projection(runways_database, airport, name, delta_y)

        frame_ = frame.copy()
        bbox_meta = None

        if contours:
            cv2.drawContours(frame_, [np.array(runway_corners_2d)], 0, (0, 255, 0), 3)

        if bbox:

            runway_corners_image = GESCamera.image_boundary(self.height, self.width, runway_corners_2d)

            for points in runway_corners_image:
                cv2.circle(frame_, (int(points[0]), int(points[1])), 5, [0, 0, 255], thickness=-1)

            cv2.drawContours(frame_, [np.array([runway_corners_image])], 0, (0, 255, 0), 2)
            x, y, w, h = cv2.boundingRect(np.array(runway_corners_image))
            bbox_meta = [[x,y],[x+w, y+h]]

            # cv2.rectangle(frame_, (x, y), (x + w, y + h), (255, 0, 0), 3)

            # cv2.namedWindow('bbox', 0)
            # cv2.imshow('bbox', frame[y:y+h, x:x+w,:])
            # cv2.waitKey(1)

        if corners:
            for points in runway_corners_2d:
                cv2.circle(frame_, (int(points[0]), int(points[1])), 5, [0, 0, 255], thickness=-1)

        if centerline:
            cv2.line(frame_, tuple(runway_axis_2d[0]), tuple(runway_axis_2d[1]), (0, 255, 255), 2)

        if sidelines:
            cv2.line(frame_, tuple(runway_corners_2d[0]), tuple(runway_corners_2d[3]), (255, 255, 0), 2)
            cv2.line(frame_, tuple(runway_corners_2d[1]), tuple(runway_corners_2d[2]), (255, 255, 0), 2)


        print("NB CORNERS %d"%len(runway_corners_image))

        return frame_, runway_corners_image, bbox_meta



    def display_runway_centerline(self, frame, runways_database, airport, name):

        runway_corners_2d = self.compute_runway_corners_projection(runways_database, airport, name)
        runway_axis_2d = self.compute_runway_axis_projection(runways_database, airport, name)
        camera_projected_position = GESCamera.projection3d_2d(self.intrinsics, self.extrinsics, [self.projected_position_along_track])

        frame_ = frame.copy()
        cv2.line(frame_, tuple(camera_projected_position[0]), tuple(runway_axis_2d[1]), (0, 255, 255), 3)

        cv2.line(frame_, tuple(runway_corners_2d[0]), tuple(runway_corners_2d[3]), (0, 255, 0), 2)
        cv2.line(frame_, tuple(runway_corners_2d[1]), tuple(runway_corners_2d[2]), (0, 255, 0), 2)

        cv2.namedWindow('Frame', 0)
        cv2.imshow('Frame', frame_)
        cv2.waitKey(1)

        return frame_



    def compute(self, runways_database, airport, runway):

        runway_points = runways_database[airport][runway]
        runway_pts = [list(runway_points['A']['position'].values()),
                             list(runway_points['B']['position'].values()),
                             list(runway_points['C']['position'].values()),
                             list(runway_points['D']['position'].values())]

        _, ltp = find_center([list(runway_points['C']['position'].values()), list(runway_points['D']['position'].values())])
        _, fpap = find_center([list(runway_points['A']['position'].values()), list(runway_points['B']['position'].values())])

        # Warning: 4 points bestfit produces differents plan.normal depending on the order of the points.
        # It is a problem, especially for computing the right values for 'height_above_runway'
        self.runway_plane = fit_3d_plane_from_points(runway_pts)
        centerline_vector = (np.array(ltp) - np.array(fpap)) / np.linalg.norm(np.array(ltp) - np.array(fpap))
        self.projected_position_on_runway_plane = projection_3d_point_on_plane(np.array(list(self.position.values())), self.runway_plane)
        self.projected_position_along_track = closest_point_on_line(np.array(ltp), np.array(fpap), self.projected_position_on_runway_plane)


        # The lateral path angle reference point is located 3050 meters along the extended runway centerline from the runway
        # reference point. At this distance, 4 deg of full angular width gives a standard 700 ft full width at the threshold,
        # which is the standard used in WAAS LPV approaches and is consistent with existing localizers
        # (scaled between 3 deg and 6 deg to achieve a 700 ft full width at the runway threshold).
        self.lateral_path_angle_reference_point = np.array(ltp) - centerline_vector * 3050


        # The vertical path angle reference point is located horizontally 305 meters along the extended runway centerline
        # from the runway reference point, and vertically at runway elevation. This is approximately 1000 ft from the threshold
        # and is consistent with most existing touchdown zones, which are commonly located 800-1200 ft from the threshold.
        self.vertical_path_angle_reference_point = np.array(ltp) - centerline_vector * 305

        # The along-track distance, or the distance along the X axis, points along the extended runway centerline but in the
        # opposite direction of the runway, such that a positive value indicates a position before the runway threshold.
        sign_along_track_distance = np.sign(get_distance_between_2_points(self.projected_position_along_track, fpap) - get_distance_between_2_points(ltp, fpap))
        self.along_track_distance = sign_along_track_distance * np.linalg.norm(self.projected_position_along_track - np.array(ltp))


        # The cross-track distance, or the distance along the Y axis, points perpendicular to the extended runway centerline,
        # such that a positive value indicates a position right of centerline from the perspective of the aircraft.
        sign_cross_track_distance = np.sign(get_distance_between_2_points(self.projected_position_on_runway_plane, runway_pts[3]) - get_distance_between_2_points(self.projected_position_on_runway_plane, runway_pts[2]))
        self.cross_track_distance = sign_cross_track_distance * np.linalg.norm(self.projected_position_on_runway_plane - self.projected_position_along_track)


        # The height above runway, or the distance along the Z axis, is defined as the difference between the aircrafts true
        # altitude and the runway elevation, such that a positive value indicates a position above runway elevation.
        # Note that it is critical to use the same datum (e.g. MSL or WGS84 HAE) for both the aircrafts altitude and
        # runway elevation in computing this height. distance_point_signed caused troubles with the normal of the plan. 
        # - patch for now: changed into 'unsigned' to always represent a position above runway.
        self.height_above_runway = self.runway_plane.distance_point(Point(list(self.position.values())))


        # The slant distance is defined as the 3D Cartesian distance from the aircraft position to the runway reference point.
        # Note that unlike the along-track distance, the slant distance will always be positive.
        self.slant_distance = np.linalg.norm(np.array(list(self.position.values()))-np.array(ltp))


        # The lateral path angle is defined as the angle in the horizontal plane formed between the runways extended centerline
        # and the line segment drawn from the lateral path angle reference point to the aircrafts position.
        # The sign is positive when the aircraft is right of the extended centerline while on the approach and
        # negative when the aircraft is left of the extended centerline. The lateral path angle differs from a
        # localizer angle in that the reference point is fixed, whereas localizers may be located at various distances
        # from the threshold depending on runway length.
        self.lateral_path_angle = sign_cross_track_distance * find_angle_between_vectors(self.lateral_path_angle_reference_point-self.projected_position_along_track,
                                                             self.lateral_path_angle_reference_point-self.projected_position_on_runway_plane)*180/np.pi


        # The vertical path angle is defined as the angle in the vertical plane formed between the local horizontal plane
        # and the line segment drawn from the vertical path angle reference point to the aircrafts position.
        # Most existing precision and APV instrument approaches have glidepath angles between 2.5 deg and 4 deg, with the majority
        # being 3 deg. The sign is positive when the aircraft is above the runway elevation. The vertical path angle differs
        # from an ILS or RNAV glideslope in that the point of intersection with the runway is fixed at the vertical path
        # angle reference point instead of varying per runway.
        self.vertical_path_angle = np.sign(self.height_above_runway)*find_angle_between_vectors(self.vertical_path_angle_reference_point-self.projected_position_along_track,
                                                             self.vertical_path_angle_reference_point-self.projected_position_along_track + self.runway_plane.normal*self.height_above_runway)*180/np.pi



