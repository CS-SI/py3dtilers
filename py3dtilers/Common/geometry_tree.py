from ..Common import ObjectsToTile


class GeometryTree():
    """
    The GeometryTree contains the root nodes and the leaf nodes of the hierarchy.
    It also contains the centroid of the root nodes.
    """

    def __init__(self, root_nodes):
        self.root_nodes = root_nodes
        self.centroid = self.get_root_objects().get_centroid()

    def set_centroid(self, centroid):
        self.centroid = centroid

    def get_leaf_nodes(self):
        """
        Return the leaf nodes of the tree.
        :return: a list of GeometryNode
        """
        leaf_nodes = list()
        for node in self.root_nodes:
            leaf_nodes.extend(node.get_leaves())
        return leaf_nodes

    def get_root_objects(self):
        """
        Return the geometries of the root nodes.
        :return: list of geometries
        """
        return ObjectsToTile([node.objects_to_tile for node in self.root_nodes])

    def get_leaf_objects(self):
        """
        Return the geometries of the leaf nodes.
        :return: list of geometries
        """
        return ObjectsToTile([node.objects_to_tile for node in self.get_leaf_nodes()])

    def get_all_objects(self):
        """
        Return the geometries of all the nodes.
        :return: list of geometries
        """
        objects = list()
        for node in self.root_nodes:
            objects.extend(node.get_objects())
        return ObjectsToTile(objects)