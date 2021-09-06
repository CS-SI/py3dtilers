import os
from os import listdir
import sys
import json
from shapely.geometry import Point, Polygon
from ..Common import ObjectsToTile
from ..Common import kd_tree


class Group():
    """
    Contains an instance of ObjectsToTile
    It can also contain additional polygon points (used to create LOA nodes)
    """

    def __init__(self, objects_to_tile, with_polygon=False, additional_points=list(), points_dict=dict()):
        self.objects_to_tile = objects_to_tile
        self.with_polygon = with_polygon
        self.additional_points = additional_points
        self.points_dict = points_dict

    def get_centroid(self):
        return self.objects_to_tile.get_centroid()

    def round_coordinates(self, coordinates, base):
        rounded_coord = coordinates
        for i in range(0, len(coordinates)):
            rounded_coord[i] = base * round(coordinates[i] / base)
        return rounded_coord


class Groups():
    """
    Contains a list of Group
    """
    def __init__(self, objects_to_tile, polygons_path=None):
        """
        Distribute the geometries contained in objects_to_tile into different Group
        The way to distribute the geometries depends on the parameters
        :param objects_to_tile: an instance of ObjectsToTile containing a list of geometries to distribute into Group
        :param polygons_path: the path to a folder containing polygons as .geojson files.
        When this param is not None, it means we want to group geometries by polygons
        """
        self.objects_to_tile = objects_to_tile
        if polygons_path is not None:
            self.group_objects_by_polygons(polygons_path)
        else:
            self.group_objects_with_kdtree()

    def get_groups_as_list(self):
        return self.groups

    def group_objects_with_kdtree(self):
        groups = list()
        objects = kd_tree(self.objects_to_tile, 500)
        for objects_to_tile in objects:
            group = Group(objects_to_tile)
            groups.append(group)
        self.groups = groups

    def group_objects_by_polygons(self, polygons_path):
        """
        Load the polygons from the files in the folder
        :param polygons_path: the path of the folder containing the files
        """
        try:
            polygon_dir = listdir(polygons_path)
        except FileNotFoundError:
            print("No directory called ", polygons_path, ". Please, place the polygons to read in", polygons_path)
            print("Exiting")
            sys.exit(1)
        polygons = list()
        # Read all the polygons in the file(s)
        for polygon_file in polygon_dir:
            if(".geojson" in polygon_file or ".json" in polygon_file):
                with open(os.path.join(polygons_path, polygon_file)) as f:
                    gjContent = json.load(f)
                for feature in gjContent['features']:
                    if feature['geometry']['type'] == 'Polygon':
                        coords = feature['geometry']['coordinates'][0][:-1]
                    if feature['geometry']['type'] == 'MultiPolygon':
                        coords = feature['geometry']['coordinates'][0][0][:-1]
                    polygons.append(Polygon(coords))
        self.groups = self.distribute_objects_in_polygons(polygons)

    def distribute_objects_in_polygons(self, polygons):
        """
        Distribute the geometries in the polygons.
        The geometries in the same polygon are grouped together. The Group created will also contain the points of the polygon.
        If a geometry is not in any polygon, create a Group containing only this geometry. This group won't have addtional points.
        """

        objects_to_tile = self.objects_to_tile
        objects_to_tile_dict = {}
        objects_to_tile_without_poly = {}

        # For each geometry, find the polygon containing it
        for i, object_to_tile in enumerate(objects_to_tile):
            p = Point(object_to_tile.get_centroid())
            in_polygon = False
            for index, polygon in enumerate(polygons):
                if p.within(polygon):
                    if index in objects_to_tile_dict:
                        objects_to_tile_dict[index].append(i)
                    else:
                        objects_to_tile_dict[index] = [i]
                    in_polygon = True
                    break
            if not in_polygon:
                objects_to_tile_without_poly[i] = [i]

        # Create a list of Group
        groups = list()
        for key in objects_to_tile_dict:
            additional_points = polygons[key].exterior.coords[:-1]
            contained_objects = ObjectsToTile([objects_to_tile[i] for i in objects_to_tile_dict[key]])
            group = Group(contained_objects, with_polygon=True, additional_points=additional_points)
            groups.append(group)
        for key in objects_to_tile_without_poly:
            contained_objects = ObjectsToTile([objects_to_tile[i] for i in objects_to_tile_without_poly[key]])
            group = Group(contained_objects)
            groups.append(group)

        return self.distribute_groups_in_cubes(groups, 300)

    def distribute_groups_in_cubes(self, groups, cube_size=300):
        """
        Merges together the groups in order to reduce the number of tiles.
        The groups are distributed into cubes of a grid. The groups in the same cube are merged together.
        To avoid conflicts, the groups with a polygon are not merged with those without polygon.
        """
        groups_dict = {}

        # Create a dictionary key: cubes center (x,y,z), with geometry (boolean); value: list of groups index
        for i in range(0, len(groups)):
            closest_cube = groups[i].round_coordinates(groups[i].get_centroid(), cube_size)
            with_polygon = groups[i].with_polygon
            if (tuple(closest_cube), with_polygon) in groups_dict:
                groups_dict[(tuple(closest_cube), with_polygon)].append(i)
            else:
                groups_dict[(tuple(closest_cube), with_polygon)] = [i]

        # Merge the groups in the same cube and create new groups
        groups_in_cube = list()
        for cube in groups_dict:
            with_polygon = cube[1]
            groups_in_cube.append(self.merge_groups_together(groups, groups_dict[cube], with_polygon))

        return groups_in_cube

    def merge_groups_together(self, groups, group_indexes, with_polygon):
        """
        Creates a Group from a list of Groups
        """

        objects = list()
        additional_points_list = list()
        additional_points_dict = dict()

        for index in group_indexes:
            if with_polygon:
                additional_points_list.append(groups[index].additional_points)
                points_index = len(additional_points_list) - 1
                additional_points_dict[points_index] = []
                for object_to_tile in groups[index].objects_to_tile:
                    objects.append(object_to_tile)
                    additional_points_dict[points_index].append(len(objects) - 1)
            else:
                for object_to_tile in groups[index].objects_to_tile:
                    objects.append(object_to_tile)
        return Group(ObjectsToTile(objects), with_polygon=with_polygon, additional_points=additional_points_list, points_dict=additional_points_dict)