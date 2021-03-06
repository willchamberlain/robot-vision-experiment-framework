import abc
import numpy as np
import logging
import database.entity
import core.image
import core.sequence_type
import core.image_source


class ImageCollection(core.image_source.ImageSource, database.entity.Entity, metaclass=abc.ABCMeta):
    """
    A collection of images stored in the database.
    This can be a sequential set of images like a video, or a random sampling of different pictures.
    """

    def __init__(self, images, type_, id_=None, **kwargs):
        super().__init__(id_=id_, **kwargs)

        self._images = images
        if (isinstance(type_, core.sequence_type.ImageSequenceType) and
                type_ is not core.sequence_type.ImageSequenceType.INTERACTIVE):
            # image collections cannot be interactive
            self._sequence_type = type_
        else:
            self._sequence_type = core.sequence_type.ImageSequenceType.NON_SEQUENTIAL

        self._is_depth_available = len(images) > 0 and all(
            hasattr(image, 'depth_data') and image.depth_data is not None for image in images.values())
        self._is_labels_image_available = len(images) > 0 and all(
            hasattr(image, 'labels_data') and image.labels_data is not None for image in images.values())
        self._is_bboxes_available = len(images) > 0 and all(
            hasattr(image, 'metadata') and hasattr(image.metadata, 'labelled_objects') and
            len(image.metadata.labelled_objects) > 0 for image in images.values())
        self._is_normals_available = len(images) > 0 and all(
            hasattr(image, 'labels_data') and image.world_normals_data is not None for image in images.values())
        self._is_stereo_available = len(images) > 0 and all(
            hasattr(image, 'left_data') and image.left_data is not None and
            hasattr(image, 'right_data') and image.right_data is not None
            for image in images.values())

        self._timestamps = sorted(self._images.keys())
        self._current_index = 0

    def __len__(self):
        """
        The length of the image collection
        :return:
        """
        return len(self._images)

    def __iter__(self):
        """
        Iterator for the image collection.
        Returns the iterator over the inner images dict
        :return:
        """
        return self._images.items()

    def __getitem__(self, item):
        """
        Allow index-based access. Why not.
        This is the same as get
        :param item:
        :return:
        """
        return self.get(item)

    @property
    def sequence_type(self):
        """
        Get the type of image sequence produced by this image source.
        This is determined when creating the image collection
        It is useful for determining which sources can run with which algorithms.
        Image collections can be NON_SEQUENTIAL or SEQUENTIAL, but not INTERACTIVE
        :return: The image sequence type enum
        :rtype core.image_sequence.ImageSequenceType:
        """
        return self._sequence_type

    @property
    def timestamps(self):
        """
        Get the list of timestamps/indexes in this collection, in order.
        They are the list of valid keys to get and __getitem__,
        all others return None
        :return:
        """
        return self._timestamps

    def begin(self):
        """
        Start producing images.
        Resets the current index to the start
        :return: True
        """
        self._current_index = 0
        return True

    def get(self, index):
        """
        A getter for random access, since we're storing a list
        :param index:
        :return:
        """
        if index in self._images:
            return self._images[index]
        return None

    def get_next_image(self):
        """
        Blocking get the next image from this source.
        Parallel versions of this may add a timeout parameter.
        Returning None indicates that this image source will produce no more images

        :return: An Image object (see core.image) or None, and a timestamp or None
        """
        if not self.is_complete():
            timestamp = self._timestamps[self._current_index]
            result = self._images[timestamp]
            self._current_index += 1
            return result, timestamp
        return None, None

    def is_complete(self):
        """
        Have we got all the images from this source?
        Some sources are infinite, some are not,
        and this method lets those that are not end the iteration.
        :return: True if there are more images to get, false otherwise.
        """
        return self._current_index >= len(self._timestamps)

    @property
    def supports_random_access(self):
        """
        Image collections support random access, they are a list of images
        :return:
        """
        return True

    @property
    def is_depth_available(self):
        """
        Do the images in this sequence include depth
        :return: True if depth is available for all images in this sequence
        """
        return self._is_depth_available

    @property
    def is_per_pixel_labels_available(self):
        """
        Do images from this image source include object lables
        :return: True if this image source can produce object labels for each image
        """
        return self._is_labels_image_available

    @property
    def is_labels_available(self):
        """
        Do images from this source include object bounding boxes in their metadata.
        :return: True iff the image metadata includes bounding boxes
        """
        return self._is_bboxes_available

    @property
    def is_normals_available(self):
        """
        Do images from this image source include world normals
        :return: True if images have world normals associated with them 
        """
        return self._is_normals_available

    @property
    def is_stereo_available(self):
        """
        Can this image source produce stereo images.
        Some algorithms only run with stereo images
        :return:
        """
        return self._is_stereo_available

    @property
    def is_stored_in_database(self):
        """
        Do this images from this source come from the database.
        Image collections are always stored in the database
        :return:
        """
        return True

    def get_camera_intrinsics(self):
        """
        Get the camera intrinisics for this image collection.
        At the moment it assumes it is the same for all images,
        and just reads it from the first.
        When I have effective metadata aggregation, read it from that.
        :return:
        """
        return self._images[0].metadata.camera_intrinsics

    def get_stereo_baseline(self):
        """
        Get the distance between the stereo cameras, or None if the images in this collection are not stereo.
        :return:
        """
        if not self.is_stereo_available or not isinstance(self._images[0], core.image.StereoImage):
            return None
        dist = self._images[0].left_camera_location - self._images[0].right_camera_location
        return np.linalg.norm(dist)

    def validate(self):
        """
        The image sequence is valid iff all the contained images are valid
        Only count the images that have a validate method
        :return: True if all the images are valid, false if not
        """
        for image in self._images:
            if hasattr(image, 'validate'):
                if not image.validate():
                    return False
        return True

    def serialize(self):
        serialized = super().serialize()
        # Only include the image IDs here, they'll get turned back into objects for us
        serialized['images'] = [(stamp, image.identifier) for stamp, image in self._images.items()]
        if self.sequence_type is core.sequence_type.ImageSequenceType.SEQUENTIAL:
            serialized['sequence_type'] = 'SEQ'
        else:
            serialized['sequence_type'] = 'NON'
        return serialized

    @classmethod
    def deserialize(cls, serialized_representation, db_client, **kwargs):
        """
        Load any collection of images.
        This handles the weird chicken-and-egg problem of deserializing
        the image collection and the individual images.

        :param serialized_representation: 
        :param db_client: An instance of database.client, from which to load the image collection
        :param kwargs: Additional arguments passed to the entity constructor.
        These will be overridden by values in serialized representation
        :return: A deserialized 
        """
        if 'images' in serialized_representation:
            s_images = db_client.image_collection.find({
                '_id': {'$in': [img_id for _, img_id in serialized_representation['images']]}
            })
            image_map = {s_image['_id']: db_client.deserialize_entity(s_image) for s_image in s_images}
            kwargs['images'] = {stamp: image_map[img_id] for stamp, img_id in serialized_representation['images']}
        if 'sequence_type' in serialized_representation and serialized_representation['sequence_type'] == 'SEQ':
            kwargs['type_'] = core.sequence_type.ImageSequenceType.SEQUENTIAL
        else:
            kwargs['type_'] = core.sequence_type.ImageSequenceType.NON_SEQUENTIAL
        return super().deserialize(serialized_representation, db_client, **kwargs)

    @classmethod
    def create_and_save(cls, db_client, image_map, sequence_type):
        """
        Make an already serialized image collection.
        Since, sometimes we have the image ids, but we don't want to have to load the objects to make the collection.
        WARNING: This can create invalid serialized image collections, since it can't check the validity of the ids.

        :param db_client: The database client, used to check image ids and for saving
        :param image_map: A map of timestamp to bson.objectid.ObjectId that refer to image objects in the database
        :param sequence_type: core.sequence_type.ImageSequenceType
        :return: The id of the newly created image collection, or None if there is an error
        """
        found_images = db_client.image_collection.find({
            '_id': {'$in': list(image_map.values())}
        }, {'_id': True}).count()
        if not found_images == len(image_map):
            logging.getLogger(__name__).warning(
                "Tried to create image collection with {0} missing ids".format(len(image_map) - found_images))
            return None
        s_images_list = [(stamp, image_id) for stamp, image_id in image_map.items()]
        s_seq_type = 'SEQ' if sequence_type is core.sequence_type.ImageSequenceType.SEQUENTIAL else 'NON'
        existing = db_client.image_source_collection.find_one({
            '_type': cls.__module__ + '.' + cls.__name__,
            'images': {'$all': s_images_list},
            'sequence_type': s_seq_type
        }, {'_id': True})
        if existing is not None:
            return existing['_id']
        else:
            return db_client.image_source_collection.insert({
                '_type': cls.__module__ + '.' + cls.__name__,
                'images': s_images_list,
                'sequence_type': s_seq_type
            })
