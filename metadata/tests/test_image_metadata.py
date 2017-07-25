import unittest
import numpy as np
import util.transform as tf
import util.dict_utils as du
import metadata.image_metadata as imeta


class TestLabelledObject(unittest.TestCase):

    def test_equals(self):
        kwargs = {
            'class_names': ('class_1',),
            'bounding_box': (152, 239, 14, 78),
            'label_color': (127, 33, 67),
            'relative_pose': tf.Transform(location=(123, -45, 23), rotation=(0.5, 0.23, 0.1)),
            'object_id': 'LabelledObject-18569'
        }
        a = imeta.LabelledObject(**kwargs)
        b = imeta.LabelledObject(**kwargs)
        self.assertEqual(a, b)
        b = imeta.LabelledObject(**du.defaults({'class_names': ('class_41',)}, kwargs))
        self.assertNotEqual(a, b)
        b = imeta.LabelledObject(**du.defaults({'bounding_box': (47, 123, 45, 121)}, kwargs))
        self.assertNotEqual(a, b)
        b = imeta.LabelledObject(**du.defaults({'label_color': (247, 123, 14)}, kwargs))
        self.assertNotEqual(a, b)
        b = imeta.LabelledObject(**du.defaults({'relative_pose': tf.Transform((62, -81, 43), (0.1, 0.1, 0.1))}, kwargs))
        self.assertNotEqual(a, b)
        b = imeta.LabelledObject(**du.defaults({'object_id': 'Cat-12'}, kwargs))
        self.assertNotEqual(a, b)

    def test_hash(self):
        kwargs = {
            'class_names': ('class_1',),
            'bounding_box': (152, 239, 14, 78),
            'label_color': (127, 33, 67),
            'relative_pose': tf.Transform(location=(123, -45, 23), rotation=(0.5, 0.23, 0.1)),
            'object_id': 'LabelledObject-18569'
        }
        a = imeta.LabelledObject(**kwargs)
        b = imeta.LabelledObject(**kwargs)
        self.assertEqual(hash(a), hash(b))
        b = imeta.LabelledObject(**du.defaults({'class_names': 'class_41'}, kwargs))
        self.assertNotEqual(hash(a), hash(b))
        b = imeta.LabelledObject(**du.defaults({'bounding_box': (47, 123, 45, 121)}, kwargs))
        self.assertNotEqual(hash(a), hash(b))
        b = imeta.LabelledObject(**du.defaults({'label_color': (247, 123, 14)}, kwargs))
        self.assertNotEqual(hash(a), hash(b))
        b = imeta.LabelledObject(**du.defaults({'relative_pose': tf.Transform((62, -81, 43), (0.1, 0.1, 0.1))}, kwargs))
        self.assertNotEqual(hash(a), hash(b))
        b = imeta.LabelledObject(**du.defaults({'object_id': 'Cat-12'}, kwargs))
        self.assertNotEqual(hash(a), hash(b))

    def test_set(self):
        a = imeta.LabelledObject(
            class_names=('class_1',),
            bounding_box=(152, 239, 14, 78),
            label_color=(127, 33, 67),
            relative_pose=tf.Transform(location=(123, -45, 23), rotation=(0.5, 0.23, 0.1)),
            object_id='LabelledObject-18569'
        )
        b = imeta.LabelledObject(
            class_names=('class_2',),
            bounding_box=(39, 169, 96, 16),
            label_color=(2, 227, 34),
            relative_pose=tf.Transform(location=(-246, 468, 4), rotation=(0.2, 0.3, 0.4)),
            object_id='LabelledObject-68478'
        )
        c = imeta.LabelledObject(
            class_names=('class_3',),
            bounding_box=(148, 468, 82, 241),
            label_color=(12, 82, 238),
            relative_pose=tf.Transform(location=(85, -648, -376), rotation=(0.8, -0.64, -0.73)),
            object_id='LabelledObject-87684'
        )
        subject_set = {a, a, a, b}
        self.assertEqual(2, len(subject_set))
        self.assertIn(a, subject_set)
        self.assertIn(b, subject_set)
        self.assertNotIn(c, subject_set)

    def test_serialize_and_deserialize(self):
        obj1 = imeta.LabelledObject(
            class_names=('class_3',),
            bounding_box=(148, 468, 82, 241),
            label_color=(12, 82, 238),
            relative_pose=tf.Transform(location=(85, -648, -376), rotation=(0.8, -0.64, -0.73)),
            object_id='LabelledObject-87684'
        )
        s_obj1 = obj1.serialize()

        obj2 = imeta.LabelledObject.deserialize(s_obj1)
        s_obj2 = obj2.serialize()

        self.assertEqual(obj1, obj2)
        self.assertEqual(s_obj1, s_obj2)

        for idx in range(100):
            # Test that repeated serialization and deserialization does not degrade the information
            obj2 = imeta.LabelledObject.deserialize(s_obj2)
            s_obj2 = obj2.serialize()
            self.assertEqual(obj1, obj2)
            self.assertEqual(s_obj1, s_obj2)


class TestImageMetadata(unittest.TestCase):

    def make_metadata(self, **kwargs):
        kwargs = du.defaults(kwargs, {
            'hash_': b'\xa5\xc9\x08\xaf$\x0b\x116',
            'source_type': imeta.ImageSourceType.SYNTHETIC,
            'environment_type': imeta.EnvironmentType.INDOOR_CLOSE,
            'light_level': imeta.LightingLevel.WELL_LIT,
            'time_of_day': imeta.TimeOfDay.DAY,

            'height': 600,
            'width': 800,
            'camera_pose': tf.Transform((1, 3, 4), (0.2, 0.8, 0.2, -0.7)),
            'right_camera_pose': tf.Transform((-10, -20, -30), (0.9, -0.7, 0.5, -0.3)),
            'fov': 90,
            'focal_length': 5,
            'aperture': 22,

            'simulation_world': 'TestSimulationWorld',
            'lighting_model': imeta.LightingModel.LIT,
            'texture_mipmap_bias': 1,
            'normal_maps_enabled': True,
            'roughness_enabled': True,
            'geometry_decimation': 0.8,

            'procedural_generation_seed': 16234,

            'labelled_objects': [
                imeta.LabelledObject(
                    class_names=('cup',),
                    bounding_box=(142, 280, 54, 78),
                    label_color=(2, 227, 34),
                    relative_pose=tf.Transform(location=(-246, 468, 4), rotation=(0.2, 0.3, 0.4)),
                    object_id='LabelledObject-68478'
                ),
                imeta.LabelledObject(
                    class_names=('car',),
                    bounding_box=(542, 83, 63, 123),
                    label_color=(26, 12, 212),
                    relative_pose=tf.Transform(location=(61, -717, 161), rotation=(0.7, 0.6, 0.3)),
                    object_id='LabelledObject-8246'
                ),
                imeta.LabelledObject(
                    class_names=('cow',),
                    bounding_box=(349, 672, 124, 208),
                    label_color=(162, 134, 163),
                    relative_pose=tf.Transform(location=(286, -465, -165), rotation=(0.9, 0.1, 0.5)),
                    object_id='LabelledObject-56485'
                )
            ],

            # Depth information
            'average_scene_depth': 90.12
        })
        return imeta.ImageMetadata(**kwargs)

    def test_constructor_works_with_minimal_parameters(self):
        imeta.ImageMetadata(source_type=imeta.ImageSourceType.SYNTHETIC, hash_=b'\x1f`\xa8\x8aR\xed\x9f\x0b',
                            height=600, width=800)

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

    def test_serialize_and_deserialize_works_with_minimal_parameters(self):
        entity1 = imeta.ImageMetadata(source_type=imeta.ImageSourceType.SYNTHETIC, hash_=b'\x1f`\xa8\x8aR\xed\x9f\x0b',
                                      height=600, width=800)
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

    def test_equals(self):
        alt_metadata = {
            'hash_': [b'\x1f`\xa8\x8aR\xed\x9f\x0b'],
            'source_type': [imeta.ImageSourceType.REAL_WORLD],
            'environment_type': [imeta.EnvironmentType.INDOOR, imeta.EnvironmentType.OUTDOOR_URBAN,
                                 imeta.EnvironmentType.OUTDOOR_LANDSCAPE],
            'light_level': [imeta.LightingLevel.PITCH_BLACK, imeta.LightingLevel.DIM, imeta.LightingLevel.EVENLY_LIT,
                            imeta.LightingLevel.BRIGHT],
            'time_of_day': [imeta.TimeOfDay.DAWN, imeta.TimeOfDay.MORNING, imeta.TimeOfDay.AFTERNOON,
                            imeta.TimeOfDay.TWILIGHT, imeta.TimeOfDay.NIGHT],
            'height': [720],
            'width': [1280],
            'camera_pose': [tf.Transform((12, 13, 14), (-0.5, 0.3, 0.8, -0.9))],
            'right_camera_pose': [tf.Transform((11, 15, 19), (-0.2, 0.4, 0.6, -0.8))],
            'fov': [30],
            'focal_length': [22],
            'aperture': [1.2],
            'simulation_world': ['TestSimulationWorld2'],
            'lighting_model': [imeta.LightingModel.UNLIT],
            'texture_mipmap_bias': [2],
            'normal_maps_enabled': [False],
            'roughness_enabled': [False],
            'geometry_decimation': [0.3],
            'procedural_generation_seed': [7329],
            'average_scene_depth': [102.33],
            'labelled_objects': [[], [
                imeta.LabelledObject(
                    class_names=('cup',),
                    bounding_box=(142, 280, 54, 78),
                    label_color=(2, 227, 34),
                    relative_pose=tf.Transform(location=(-246, 468, 4), rotation=(0.2, 0.3, 0.4)),
                    object_id='LabelledObject-68478'
                ),
                imeta.LabelledObject(
                    class_names=('cat',),
                    bounding_box=(542, 83, 63, 123),
                    label_color=(26, 12, 212),
                    relative_pose=tf.Transform(location=(61, -717, 161), rotation=(0.7, 0.6, 0.3)),
                    object_id='LabelledObject-8246'
                ),
                imeta.LabelledObject(
                    class_names=('cow',),
                    bounding_box=(349, 672, 124, 208),
                    label_color=(162, 134, 163),
                    relative_pose=tf.Transform(location=(286, -465, -165), rotation=(0.9, 0.1, 0.5)),
                    object_id='LabelledObject-56485'
                )
            ],[
                imeta.LabelledObject(
                    class_names=('cup',),
                    bounding_box=(142, 12, 54, 78),
                    label_color=(2, 227, 34),
                    relative_pose=tf.Transform(location=(-246, 468, 4), rotation=(0.2, 0.3, 0.4)),
                    object_id='LabelledObject-68478'
                ),
                imeta.LabelledObject(
                    class_names=('car',),
                    bounding_box=(542, 83, 63, 123),
                    label_color=(26, 12, 212),
                    relative_pose=tf.Transform(location=(61, -717, 161), rotation=(0.7, 0.6, 0.3)),
                    object_id='LabelledObject-8246'
                ),
                imeta.LabelledObject(
                    class_names=('cow',),
                    bounding_box=(349, 672, 124, 208),
                    label_color=(162, 134, 163),
                    relative_pose=tf.Transform(location=(286, -465, -165), rotation=(0.9, 0.1, 0.5)),
                    object_id='LabelledObject-56485'
                )
            ],[
                imeta.LabelledObject(
                    class_names=('cup',),
                    bounding_box=(142, 280, 54, 78),
                    label_color=(2, 227, 34),
                    relative_pose=tf.Transform(location=(-246, 468, 4), rotation=(0.2, 0.3, 0.4)),
                    object_id='LabelledObject-68478'
                ),
                imeta.LabelledObject(
                    class_names=('car',),
                    bounding_box=(542, 83, 63, 123),
                    label_color=(26, 12, 212),
                    relative_pose=tf.Transform(location=(61, -717, 161), rotation=(0.7, 0.6, 0.3)),
                    object_id='LabelledObject-8246'
                ),
                imeta.LabelledObject(
                    class_names=('cow',),
                    bounding_box=(349, 672, 124, 208),
                    label_color=(162, 134, 255),
                    relative_pose=tf.Transform(location=(286, -465, -165), rotation=(0.9, 0.1, 0.5)),
                    object_id='LabelledObject-56485'
                )
            ]]
        }
        a = self.make_metadata()
        b = self.make_metadata()
        self.assertEqual(a, b)

        # Change single keys, and make sure it is no longer equal
        for key, values in alt_metadata.items():
            for val in values:
                b = self.make_metadata(**{key: val})
                self.assertNotEqual(a, b, "Changing key {0} to {1} did not change equality".format(key, str(val)))

    def test_hash(self):
        alt_metadata = {
            'hash_': [b'\x1f`\xa8\x8aR\xed\x9f\x0b'],
            'source_type': [imeta.ImageSourceType.REAL_WORLD],
            'environment_type': [imeta.EnvironmentType.INDOOR, imeta.EnvironmentType.OUTDOOR_URBAN,
                                 imeta.EnvironmentType.OUTDOOR_LANDSCAPE],
            'light_level': [imeta.LightingLevel.PITCH_BLACK, imeta.LightingLevel.DIM, imeta.LightingLevel.EVENLY_LIT,
                            imeta.LightingLevel.BRIGHT],
            'time_of_day': [imeta.TimeOfDay.DAWN, imeta.TimeOfDay.MORNING, imeta.TimeOfDay.AFTERNOON,
                            imeta.TimeOfDay.TWILIGHT, imeta.TimeOfDay.NIGHT],
            'height': [720],
            'width': [1280],
            'camera_pose': [tf.Transform((12, 13, 14), (-0.5, 0.3, 0.8, -0.9))],
            'right_camera_pose': [tf.Transform((11, 15, 19), (-0.2, 0.4, 0.6, -0.8))],
            'fov': [30],
            'focal_length': [22],
            'aperture': [1.2],
            'simulation_world': ['TestSimulationWorld2'],
            'lighting_model': [imeta.LightingModel.UNLIT],
            'texture_mipmap_bias': [2],
            'normal_maps_enabled': [False],
            'roughness_enabled': [False],
            'geometry_decimation': [0.3],
            'procedural_generation_seed': [7329],
            'average_scene_depth': [102.33],
            'labelled_objects': [[], [
                imeta.LabelledObject(
                    class_names=('cup',),
                    bounding_box=(142, 280, 54, 78),
                    label_color=(2, 227, 34),
                    relative_pose=tf.Transform(location=(-246, 468, 4), rotation=(0.2, 0.3, 0.4)),
                    object_id='LabelledObject-68478'
                ),
                imeta.LabelledObject(
                    class_names=('cat',),
                    bounding_box=(542, 83, 63, 123),
                    label_color=(26, 12, 212),
                    relative_pose=tf.Transform(location=(61, -717, 161), rotation=(0.7, 0.6, 0.3)),
                    object_id='LabelledObject-8246'
                ),
                imeta.LabelledObject(
                    class_names=('cow',),
                    bounding_box=(349, 672, 124, 208),
                    label_color=(162, 134, 163),
                    relative_pose=tf.Transform(location=(286, -465, -165), rotation=(0.9, 0.1, 0.5)),
                    object_id='LabelledObject-56485'
                )
            ], [
                imeta.LabelledObject(
                    class_names=('cup',),
                    bounding_box=(142, 12, 54, 78),
                    label_color=(2, 227, 34),
                    relative_pose=tf.Transform(location=(-246, 468, 4), rotation=(0.2, 0.3, 0.4)),
                    object_id='LabelledObject-68478'
                ),
                imeta.LabelledObject(
                    class_names=('car',),
                    bounding_box=(542, 83, 63, 123),
                    label_color=(26, 12, 212),
                    relative_pose=tf.Transform(location=(61, -717, 161), rotation=(0.7, 0.6, 0.3)),
                    object_id='LabelledObject-8246'
                ),
                imeta.LabelledObject(
                    class_names=('cow',),
                    bounding_box=(349, 672, 124, 208),
                    label_color=(162, 134, 163),
                    relative_pose=tf.Transform(location=(286, -465, -165),
                                               rotation=(0.9, 0.1, 0.5)),
                    object_id='LabelledObject-56485'
                )
            ], [
                imeta.LabelledObject(
                    class_names=('cup',),
                    bounding_box=(142, 280, 54, 78),
                    label_color=(2, 227, 34),
                    relative_pose=tf.Transform(location=(-246, 468, 4), rotation=(0.2, 0.3, 0.4)),
                    object_id='LabelledObject-68478'
                ),
                imeta.LabelledObject(
                    class_names=('car',),
                    bounding_box=(542, 83, 63, 123),
                    label_color=(26, 12, 212),
                    relative_pose=tf.Transform(location=(61, -717, 161), rotation=(0.7, 0.6, 0.3)),
                    object_id='LabelledObject-8246'
                ),
                imeta.LabelledObject(
                    class_names=('cow',),
                    bounding_box=(349, 672, 124, 208),
                    label_color=(162, 134, 255),
                    relative_pose=tf.Transform(location=(286, -465, -165),
                                               rotation=(0.9, 0.1, 0.5)),
                    object_id='LabelledObject-56485'
                )
            ]]
        }
        a = self.make_metadata()
        b = self.make_metadata()
        self.assertEqual(hash(a), hash(b))

        # Change single keys, and make sure it is no longer equal
        for key, values in alt_metadata.items():
            for val in values:
                b = self.make_metadata(**{key: val})
                self.assertNotEqual(hash(a), hash(b),
                                    "Changing key {0} to {1} did not change the hash".format(key, str(val)))

    def assert_metadata_equal(self, metadata1, metadata2):
        if not isinstance(metadata1, imeta.ImageMetadata):
            self.fail("metadata 1 is not an image metadata")
        if not isinstance(metadata2, imeta.ImageMetadata):
            self.fail("metadata 1 is not an image metadata")
        self.assertEqual(metadata1.hash, metadata2.hash)
        self.assertEqual(metadata1.source_type, metadata2.source_type)
        self.assertEqual(metadata1.environment_type, metadata2.environment_type)
        self.assertEqual(metadata1.light_level, metadata2.light_level)
        self.assertEqual(metadata1.time_of_day, metadata2.time_of_day)
        self.assertEqual(metadata1.height, metadata2.height)
        self.assertEqual(metadata1.width, metadata2.width)
        self.assertEqual(metadata1.camera_pose, metadata2.camera_pose)
        self.assertEqual(metadata1.right_camera_pose, metadata2.right_camera_pose)
        self.assertEqual(metadata1.fov, metadata2.fov)
        self.assertEqual(metadata1.focal_length, metadata2.focal_length)
        self.assertEqual(metadata1.aperture, metadata2.aperture)
        self.assertEqual(metadata1.simulation_world, metadata2.simulation_world)
        self.assertEqual(metadata1.lighting_model, metadata2.lighting_model)
        self.assertEqual(metadata1.texture_mipmap_bias, metadata2.texture_mipmap_bias)
        self.assertEqual(metadata1.normal_maps_enabled, metadata2.normal_maps_enabled)
        self.assertEqual(metadata1.roughness_enabled, metadata2.roughness_enabled)
        self.assertEqual(metadata1.geometry_decimation, metadata2.geometry_decimation)
        self.assertEqual(metadata1.procedural_generation_seed, metadata2.procedural_generation_seed)
        self.assertEqual(metadata1.labelled_objects, metadata2.labelled_objects)
        self.assertEqual(metadata1.average_scene_depth, metadata2.average_scene_depth)
