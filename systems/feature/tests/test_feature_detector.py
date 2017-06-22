import unittest
import abc
import numpy as np
import cv2
import bson.objectid
import util.transform as tf
import metadata.image_metadata as imeta
import core.image_entity
import core.trial_result
import systems.feature.feature_detector_result
import systems.feature.feature_detector


def create_mock_image(width=128, height=128):
    """
    Make an image by drawing a bunch of semi-transparent squares
    This should actually have discernible features, in contrast to pure noise
    :param width:
    :param height:
    :return:
    """
    im = np.zeros((width, height, 3), dtype='uint8')
    for _ in range(10):
        shape = (np.random.randint(width), np.random.randint(height))
        position = (np.random.randint(1 - shape[0], width), np.random.randint(1 - shape[1], height))
        colour = np.random.randint(0, 256, 3, dtype='uint8')
        im[max(0, position[1]):min(height, position[1] + shape[1]),
           max(0, position[0]):min(width, position[0] + shape[0]), :] += colour

    metadata = imeta.ImageMetadata(source_type=imeta.ImageSourceType.SYNTHETIC,
                                   environment_type=imeta.EnvironmentType.INDOOR_CLOSE,
                                   light_level=imeta.LightingLevel.WELL_LIT,
                                   time_of_day=imeta.TimeOfDay.DAY,
                                   height=height,
                                   width=width,
                                   fov=90,
                                   focal_length=100,
                                   aperture=22)
    return core.image_entity.ImageEntity(data=im,
                                         metadata=metadata,
                                         camera_pose=tf.Transform(),
                                         id_=bson.objectid.ObjectId())


class FeatureDetectorContract(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def make_instance(self, *args, **kwargs):
        """
        Make a new instance of the feature detector
        :return: A new instance to test
        """
        pass

    @abc.abstractmethod
    def get_config_attributes(self):
        """
        Get the attributes which affect the system settings.
        I couldn't find a good way to filter these from the object methods
        :return:
        """
        return []

    def test_no_properties_can_change_during_test(self):
        subject = self.make_instance()
        candidate_values = [None, 10, 0, 0.1, [], {}]
        initial_settings = subject.get_system_settings()
        subject.start_trial()
        for attr in self.get_config_attributes():
            if hasattr(subject, attr):
                for value in candidate_values:
                    setattr(subject, attr, value)
                    self.assertEqual(initial_settings,subject.get_system_settings(),
                                     "Attribute {0} was changed after test started".format(attr))

    def test_finish_trial_produces_trial_result(self):
        subject = self.make_instance()
        subject.start_trial()
        for idx in range(10):
            image = create_mock_image()
            subject.process_image(image, idx)
        result = subject.finish_trial()
        self.assertIsInstance(result, core.trial_result.TrialResult)
        self.assertTrue(result.success)

    def test_detects_features_and_stores_in_result(self):
        subject = self.make_instance()
        subject.start_trial()
        object_ids = []
        for idx in range(10):
            image = create_mock_image()
            object_ids.append(image.identifier)
            subject.process_image(image, idx)
        result = subject.finish_trial()
        self.assertIsInstance(result, systems.feature.feature_detector_result.FeatureDetectorResult)
        for object_id in object_ids:
            self.assertIn(object_id, result.keypoints)
            self.assertGreater(len(result.keypoints[object_id]), 0)

    def test_stores_settings_in_results(self):
        subject = self.make_instance()
        initial_settings = subject.get_system_settings()
        subject.start_trial()
        for idx in range(10):
            image = create_mock_image()
            subject.process_image(image, idx)
        result = subject.finish_trial()
        self.assertEqual(initial_settings, result.settings)


class VoidDetector:
    """
    This is the minimal API we expect for feature detectors returned by make_detector
    """
    def detect(self, image_mat, mask):
        width, height = image_mat.shape
        return [cv2.KeyPoint(x=np.random.uniform(width),
                             y=np.random.uniform(height),
                             _angle=np.random.uniform(360),
                             _class_id=-1,
                             _octave=np.random.randint(100000000),
                             _response=np.random.uniform(0, 1),
                             _size=np.random.uniform(10))
                for _ in range(30)]


class MockFeatureDetector(systems.feature.feature_detector.FeatureDetector):
    """
    This is the minimum non-trivial amount needed to pass the feature detector tests
    """

    def __init__(self, id_=None):
        super().__init__(id_=id_)
        self._distance = 10

    @property
    def distance(self):
        return self._distance

    @distance.setter
    def distance(self, dist):
        if not self.is_trial_running():
            self.distance = dist

    def make_detector(self):
        """
        Make the cv2 detector for this system.
        Call the constructor
        :return:
        """
        return VoidDetector()

    def get_system_settings(self):
        """
        Get the settings values used by the detector
        :return:
        """
        return {'distance': self.distance}


class TestFeatureDetector(FeatureDetectorContract, unittest.TestCase):
    """
    Test the Feature Detector base class. It needs to meet it's own criteria with a minimal detector
    """
    def make_instance(self, *args, **kwargs):
        return MockFeatureDetector(*args, **kwargs)

    def get_config_attributes(self):
        return ['distance']