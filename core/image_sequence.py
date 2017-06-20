import abc
import pymongo
import database.entity
import core.image
import core.sequence_type
import core.image_source


class ImageSequence(core.image_source.ImageSource, database.entity.Entity, metaclass=abc.ABCMeta):
    """
    A timestamped sequence of images, the camera following a path through space.
    This is
    """

    def __init__(self, images, id_=None, **kwargs):
        super().__init__(id_=id_, **kwargs)
        self._images = images
        self._is_depth_available = len(images) > 0 and all(hasattr(image, 'depth_filename') and
                                                           image.depth_data is not None for image in images.values())
        self._is_labels_available = len(images) > 0 and all(hasattr(image, 'labels_filename') and
                                                            image.labels_data is not None for image in images.values())
        self._is_normals_available = len(images) > 0 and all(hasattr(image, 'labels_filename') and
                                                             image.world_normals_data is not None
                                                             for image in images.values())
        self._is_stereo_available = len(images) > 0 and all(hasattr(image, 'left_filename') and
                                                            hasattr(image, 'right_filename')
                                                            for image in images.values())
        self._timestamps = list(images.keys())
        self._timestamps.sort()
        self._current_index = 0

    def __len__(self):
        return len(self._images)

    def __iter__(self):
        """
        Iterator for the image collection
        :return:
        """
        return iter(self._images)

    def __getitem__(self, timestamp):
        """
        Allow index-based access. Why not.
        :param timestamp:
        :return:
        """
        return self.get(timestamp)

    def get(self, timestamp):
        """
        A getter for random access, since we're storing a list
        :param timestamp:
        :return:
        """
        if timestamp in self._images:
            return self._images[timestamp]
        return None

    @property
    def sequence_type(self):
        """
        Get the type of image sequence produced by this image source.
        Image Sequences are always sequential
        :return: The image sequence type enum
        :rtype core.image_sequence.ImageSequenceType:
        """
        return core.sequence_type.ImageSequenceType.SEQUENTIAL

    def begin(self):
        """
        Start producing images.
        Resets the current index to the start
        :return: True
        """
        self._current_index = 0
        return True

    def get_next_image(self):
        """
        Blocking get the next image from this source.
        Parallel versions of this may add a timeout parameter.
        Returning None indicates that this image source will produce no more images

        :return: An Image object (see core.image) or None
        """
        if not self.is_complete():
            timestamp = self._timestamps[self._current_index]
            image = self._images[timestamp]
            self._current_index += 1
            return image
        return None

    def is_complete(self):
        """
        Have we got all the images from this source?
        Some sources are infinite, some are not,
        and this method lets those that are not end the iteration.
        :return: True if there are more images to get, false otherwise.
        """
        return self._current_index >= len(self._timestamps)

    @property
    def is_depth_available(self):
        """
        Do the images in this sequence include depth
        :return: True if depth is available for all images in this sequence
        """
        return self._is_depth_available

    @property
    def is_labels_available(self):
        """
        Do images from this image source include object lables
        :return: True if this image source can produce object labels for each image
        """
        return self._is_labels_available

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
        serialized['images'] = [{
            'timestamp': timestamp,
            'image': image.identifier
        } for timestamp, image in self._images.items()]
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
                '_id': {'$in': [m['image'] for m in serialized_representation['images']]}
            })
            image_map = {s_image['_id']: db_client.deserialize_entity(s_image) for s_image in s_images}
            kwargs['images'] = {m['timestamp']: image_map[m['image']] for m in serialized_representation['images']}
        return super().deserialize(serialized_representation, db_client, **kwargs)

    @classmethod
    def create_serialized(cls, image_ids, sequence_type):
        """
        Make an already serialized image collection.
        Since, sometimes we have the image ids, but we don't want to have to load the objects to make the collection.
        WARNING: This can create invalid serialized image collections, since it can't check the validity of the ids.

        :param image_ids: A list of bson.objectid.ObjectId that refer to image objects in the database
        :param sequence_type: core.sequence_type.ImageSequenceType
        :return:
        """
        return {
            '_type': cls.__name__,
            'images': image_ids,
            'sequence_type': 'SEQ' if sequence_type is core.sequence_type.ImageSequenceType.SEQUENTIAL else 'NON'
        }