import unittest
import numpy as np
import util.dict_utils as du
import metadata.image_metadata as imeta


class TestBoundingBox(unittest.TestCase):

    def test_equals(self):
        kwargs = {
            'class_name': 'class_' + str(np.random.randint(255)),
            'confidence': np.random.uniform(0, 1),
            'x': np.random.randint(800),
            'y': np.random.randint(600),
            'width': np.random.randint(128),
            'height': np.random.randint(128)
        }
        a = imeta.BoundingBox(**kwargs)
        b = imeta.BoundingBox(**kwargs)
        c = imeta.BoundingBox(
            class_name='class_' + str(np.random.randint(255)),
            confidence=np.random.uniform(0, 1),
            x=np.random.randint(800),
            y=np.random.randint(600),
            width=np.random.randint(128),
            height=np.random.randint(128)
        )
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertNotEqual(b, c)

    def test_hash(self):
        kwargs = {
            'class_name': 'class_' + str(np.random.randint(255)),
            'confidence': np.random.uniform(0, 1),
            'x': np.random.randint(800),
            'y': np.random.randint(600),
            'width': np.random.randint(128),
            'height': np.random.randint(128)
        }
        a = imeta.BoundingBox(**kwargs)
        b = imeta.BoundingBox(**kwargs)
        c = imeta.BoundingBox(
            class_name='class_' + str(np.random.randint(255)),
            confidence=np.random.uniform(0, 1),
            x=np.random.randint(800),
            y=np.random.randint(600),
            width=np.random.randint(128),
            height=np.random.randint(128)
        )
        self.assertEqual(hash(a), hash(b))
        self.assertNotEqual(hash(a), hash(c))
        self.assertNotEqual(hash(b), hash(c))

    def test_set(self):
        a = imeta.BoundingBox(
            class_name='class_' + str(np.random.randint(255)),
            confidence=np.random.uniform(0, 1),
            x=np.random.randint(800),
            y=np.random.randint(600),
            width=np.random.randint(128),
            height=np.random.randint(128)
        )
        b = imeta.BoundingBox(
            class_name='class_' + str(np.random.randint(255)),
            confidence=np.random.uniform(0, 1),
            x=np.random.randint(800),
            y=np.random.randint(600),
            width=np.random.randint(128),
            height=np.random.randint(128)
        )
        c = imeta.BoundingBox(
            class_name='class_' + str(np.random.randint(255)),
            confidence=np.random.uniform(0, 1),
            x=np.random.randint(800),
            y=np.random.randint(600),
            width=np.random.randint(128),
            height=np.random.randint(128)
        )
        subject_set = {a, a, a, b}
        self.assertEqual(2, len(subject_set))
        self.assertIn(a, subject_set)
        self.assertIn(b, subject_set)
        self.assertNotIn(c, subject_set)

    def test_serialize_and_deserialize(self):
        bbox1 = imeta.BoundingBox(
            class_name='class_' + str(np.random.randint(255)),
            confidence=np.random.uniform(0, 1),
            x=np.random.randint(800),
            y=np.random.randint(600),
            width=np.random.randint(128),
            height=np.random.randint(128)
        )
        s_bbox1 = bbox1.serialize()

        bbox2 = imeta.BoundingBox.deserialize(s_bbox1)
        s_bbox2 = bbox2.serialize()

        self.assertEqual(bbox1, bbox2)
        self.assertEqual(s_bbox1, s_bbox2)

        for idx in range(100):
            # Test that repeated serialization and deserialization does not degrade the information
            bbox2 = imeta.BoundingBox.deserialize(s_bbox2)
            s_bbox2 = bbox2.serialize()
            self.assertEqual(bbox1, bbox2)
            self.assertEqual(s_bbox1, s_bbox2)


class TestImageMetadata(unittest.TestCase):

    def make_metadata(self, **kwargs):
        kwargs = du.defaults(kwargs, {
            'source_type': imeta.ImageSourceType.SYNTHETIC,
            'environment_type': imeta.EnvironmentType.INDOOR_CLOSE,
            'light_level': imeta.LightingLevel.WELL_LIT,
            'time_of_day': imeta.TimeOfDay.DAY,

            'height': 600,
            'width': 800,
            'fov': 90,
            'focal_length': 5,
            'aperture': 22,

            'simulation_world': 'TestSimulationWorld',
            'lighting_model': imeta.LightingModel.LIT,
            'texture_mipmap_bias': 1,
            'normal_mipmap_bias': 2,
            'roughness_enabled': True,
            'geometry_decimation': 0.8,

            'procedural_generation_seed': 16234,

            'label_classes': ['cup', 'car', 'cow'],
            'label_bounding_boxes': [
                imeta.BoundingBox('cup', 0.883, 142, 280, 54, 78),
                imeta.BoundingBox('car', 0.912, 542, 83, 63, 123),
                imeta.BoundingBox('cow', 0.6778, 349, 672, 124, 208)
            ],
            'distances_to_labelled_objects': {'cup': 1.223, 'car': 15.9887, 'cow': 102.63},

            # Depth information
            'average_scene_depth': 90.12
        })
        return imeta.ImageMetadata(**kwargs)

    def test_constructor_works_with_minimal_parameters(self):
        imeta.ImageMetadata(source_type=imeta.ImageSourceType.SYNTHETIC,
                            environment_type=imeta.EnvironmentType.INDOOR_CLOSE,
                            light_level=imeta.LightingLevel.WELL_LIT,
                            time_of_day=imeta.TimeOfDay.DAY,
                            height=600,
                            width=800,
                            fov=90,
                            focal_length=100,
                            aperture=22)

    def test_serialize_and_deserialise(self):
        entity1 = self.make_metadata()
        s_entity1 = entity1.serialize()

        entity2 = imeta.ImageMetadata.deserialize(s_entity1)
        s_entity2 = entity2.serialize()

        self.assert_metadata_equal(entity1, entity2)
        self.assertEqual(s_entity1, s_entity2)

        for idx in range(100):
            # Test that repeated serialization and deserialization does not degrade the information
            entity2 = imeta.ImageMetadata.deserialize(s_entity2)
            s_entity2 = entity2.serialize()
            self.assert_metadata_equal(entity1, entity2)
            self.assertEqual(s_entity1, s_entity2)

    def assert_metadata_equal(self, metadata1, metadata2):
        if not isinstance(metadata1, imeta.ImageMetadata):
            self.fail("metadata 1 is not an image metadata")
        if not isinstance(metadata2, imeta.ImageMetadata):
            self.fail("metadata 1 is not an image metadata")
        self.assertEqual(metadata1.source_type, metadata2.source_type)
        self.assertEqual(metadata1.environment_type, metadata2.environment_type)
        self.assertEqual(metadata1.light_level, metadata2.light_level)
        self.assertEqual(metadata1.time_of_day, metadata2.time_of_day)
        self.assertEqual(metadata1.height, metadata2.height)
        self.assertEqual(metadata1.width, metadata2.width)
        self.assertEqual(metadata1.fov, metadata2.fov)
        self.assertEqual(metadata1.focal_length, metadata2.focal_length)
        self.assertEqual(metadata1.aperture, metadata2.aperture)
        self.assertEqual(metadata1.simulation_world, metadata2.simulation_world)
        self.assertEqual(metadata1.lighting_model, metadata2.lighting_model)
        self.assertEqual(metadata1.texture_mipmap_bias, metadata2.texture_mipmap_bias)
        self.assertEqual(metadata1.normal_mipmap_bias, metadata2.normal_mipmap_bias)
        self.assertEqual(metadata1.roughness_enabled, metadata2.roughness_enabled)
        self.assertEqual(metadata1.geometry_decimation, metadata2.geometry_decimation)
        self.assertEqual(metadata1.procedural_generation_seed, metadata2.procedural_generation_seed)
        self.assertEqual(metadata1.label_classes, metadata2.label_classes)
        self.assertEqual(metadata1.label_bounding_boxes, metadata2.label_bounding_boxes)
        self.assertEqual(metadata1.distances_to_labelled_objects, metadata2.distances_to_labelled_objects)
        self.assertEqual(metadata1.average_scene_depth, metadata2.average_scene_depth)
