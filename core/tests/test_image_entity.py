import unittest
import unittest.mock as mock
import numpy as np
import gridfs
import pickle
import util.dict_utils as du
import util.transform as tf
import metadata.image_metadata as imeta
import database.tests.test_entity as entity_test
import core.image
import core.image_entity as ie


class MockReadable:
    """
    A helper for mock gridfs.get to return, that has a 'read' method as expected.
    """
    def __init__(self, thing):
        self._thing_bytes = pickle.dumps(thing, protocol=pickle.HIGHEST_PROTOCOL)

    def read(self):
        return self._thing_bytes


class TestImageEntity(entity_test.EntityContract, unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.data_map = [
            np.asarray(np.random.uniform(0, 255, (32, 32, 3)), dtype='uint8'),
            np.asarray(np.random.uniform(0, 255, (32, 32, 3)), dtype='uint8'),
            np.asarray(np.random.uniform(0, 255, (32, 32, 3)), dtype='uint8'),
            np.asarray(np.random.uniform(0, 255, (32, 32, 3)), dtype='uint8')
        ]

    def get_class(self):
        return ie.ImageEntity

    def make_instance(self, *args, **kwargs):
        kwargs = du.defaults(kwargs, {
            'data': self.data_map[0],
            'data_id': 0,
            'camera_pose': tf.Transform(location=(1, 2, 3),
                                        rotation=(4, 5, 6, 7)),
            'metadata': imeta.ImageMetadata(
                source_type=imeta.ImageSourceType.SYNTHETIC,
                environment_type=imeta.EnvironmentType.INDOOR_CLOSE,
                light_level=imeta.LightingLevel.WELL_LIT,
                time_of_day=imeta.TimeOfDay.DAY,
                height=600,
                width=800,
                fov=90,
                focal_length=5,
                aperture=22,
                simulation_world='TestSimulationWorld',
                lighting_model=imeta.LightingModel.LIT,
                texture_mipmap_bias=1,
                normal_mipmap_bias=2,
                roughness_enabled=True,
                geometry_decimation=0.8,
                procedural_generation_seed=16234,
                label_classes=['cup', 'car', 'cow'],
                label_bounding_boxes={imeta.BoundingBox(class_name='cup', confidence=1,
                                                        x=10, y=65, height=24, width=97)},
                distances_to_labelled_objects={'cup': 1.223, 'car': 15.9887, 'cow': 102.63},
                average_scene_depth=90.12),
            'additional_metadata': {
                'Source': 'Generated',
                'Resolution': {'width': 1280, 'height': 720},
                'Material Properties': {
                    'BaseMipMapBias': 0,
                    'RoughnessQuality': True
                }
            },
            'depth_data': self.data_map[1],
            'depth_id': 1,
            'labels_data': self.data_map[2],
            'labels_id': 2,
            'world_normals_data': self.data_map[3],
            'world_normals_id': 3
        })
        return ie.ImageEntity(*args, **kwargs)

    def create_mock_db_client(self):
        self.db_client = super().create_mock_db_client()

        self.db_client.grid_fs = unittest.mock.create_autospec(gridfs.GridFS)
        self.db_client.grid_fs.get.side_effect = lambda id_: MockReadable(self.data_map[id_])

        return self.db_client

    def assert_models_equal(self, image1, image2):
        """
        Helper to assert that two image entities are equal
        :param image1: ImageEntity
        :param image2: ImageEntity
        :return:
        """
        if not isinstance(image1, ie.ImageEntity) or not isinstance(image2, ie.ImageEntity):
            self.fail('object was not an Image')
        self.assertEqual(image1.identifier, image2.identifier)
        self.assertTrue(np.array_equal(image1.data, image2.data))
        self.assertEqual(image1.camera_pose, image2.camera_pose)
        self.assertTrue(np.array_equal(image1.depth_data, image2.depth_data))
        self.assertTrue(np.array_equal(image1.labels_data, image2.labels_data))
        self.assertTrue(np.array_equal(image1.world_normals_data, image2.world_normals_data))
        self.assertEqual(image1.additional_metadata, image2.additional_metadata)

    def test_constructor_works_with_minimal_arguments(self):
        ie.ImageEntity(data=np.random.randint(0, 255, (256, 256, 3), dtype='uint8'),
                       camera_pose=tf.Transform(),
                       metadata=imeta.ImageMetadata(
                           source_type=imeta.ImageSourceType.SYNTHETIC,
                           height=600,
                           width=800
                       ))

    def test_serialize_and_deserialize_works_with_minimal_arguments(self):
        entity1 = ie.ImageEntity(data=self.data_map[0],
                                 data_id=0,
                                 camera_pose=tf.Transform(),
                                 metadata=imeta.ImageMetadata(
                                     source_type=imeta.ImageSourceType.SYNTHETIC,
                                     height=600,
                                     width=800
                                 ))
        s_entity = entity1.serialize()
        entity2 = ie.ImageEntity.deserialize(s_entity, self.create_mock_db_client())
        s_entity2 = entity2.serialize()
        self.assert_models_equal(entity1, entity2)
        self.assert_serialized_equal(s_entity, s_entity2)

    def test_deserialise_calls_gridfs(self):
        mock_db_client = self.create_mock_db_client()
        EntityClass = self.get_class()
        entity = self.make_instance(id_=12345)
        s_entity = entity.serialize()

        self.assertFalse(mock_db_client.grid_fs.get.called)
        EntityClass.deserialize(s_entity, mock_db_client)
        self.assertTrue(mock_db_client.grid_fs.get.called)
        self.assertEqual(4, mock_db_client.grid_fs.get.call_count)
        self.assertIn(mock.call(s_entity['data']), mock_db_client.grid_fs.get.call_args_list)
        self.assertIn(mock.call(s_entity['depth_data']), mock_db_client.grid_fs.get.call_args_list)
        self.assertIn(mock.call(s_entity['labels_data']), mock_db_client.grid_fs.get.call_args_list)
        self.assertIn(mock.call(s_entity['world_normals_data']), mock_db_client.grid_fs.get.call_args_list)

    def test_does_not_deserialize_from_null_id(self):
        mock_db_client = self.create_mock_db_client()
        EntityClass = self.get_class()
        entity = self.make_instance(id_=12345)
        s_entity = entity.serialize()
        s_entity['depth_data'] = None
        s_entity['labels_data'] = None
        s_entity['world_normals_data'] = None

        self.assertFalse(mock_db_client.grid_fs.get.called)
        EntityClass.deserialize(s_entity, mock_db_client)
        self.assertEqual(1, mock_db_client.grid_fs.get.call_count)

    def test_save_image_data_stores_in_gridfs(self):
        mock_db_client = self.create_mock_db_client()
        entity = self.make_instance(data_id=None,
                                    depth_id=None,
                                    labels_id=None,
                                    world_normals_id=None)
        entity.save_image_data(mock_db_client)
        self.assertTrue(mock_db_client.grid_fs.put.called)
        self.assertEqual(4, mock_db_client.grid_fs.put.call_count)

    def test_save_image_data_does_not_store_data_if_already_stored(self):
        mock_db_client = self.create_mock_db_client()
        entity = self.make_instance()
        entity.save_image_data(mock_db_client, force_update=False)
        self.assertFalse(mock_db_client.grid_fs.put.called)

    def test_save_image_data_updates_ids(self):
        mock_db_client = self.create_mock_db_client()
        entity = self.make_instance(data_id=None,
                                    depth_id=None,
                                    labels_id=None,
                                    world_normals_id=None)
        ids = [i for i in range(400, 800, 100)]
        mock_db_client.grid_fs.put.side_effect = ids
        entity.save_image_data(mock_db_client)
        s_entity = entity.serialize()
        self.assertIn(s_entity['data'], ids)
        self.assertIn(s_entity['depth_data'], ids)
        self.assertIn(s_entity['labels_data'], ids)
        self.assertIn(s_entity['world_normals_data'], ids)


class TestStereoImageEntity(entity_test.EntityContract, unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.data_map = [
            np.asarray(np.random.uniform(0, 255, (32, 32, 3)), dtype='uint8'),
            np.asarray(np.random.uniform(0, 255, (32, 32, 3)), dtype='uint8'),
            np.asarray(np.random.uniform(0, 255, (32, 32, 3)), dtype='uint8'),
            np.asarray(np.random.uniform(0, 255, (32, 32, 3)), dtype='uint8'),
            np.asarray(np.random.uniform(0, 255, (32, 32, 3)), dtype='uint8'),
            np.asarray(np.random.uniform(0, 255, (32, 32, 3)), dtype='uint8'),
            np.asarray(np.random.uniform(0, 255, (32, 32, 3)), dtype='uint8'),
            np.asarray(np.random.uniform(0, 255, (32, 32, 3)), dtype='uint8')
        ]

    def get_class(self):
        return ie.StereoImageEntity

    def make_instance(self, *args, **kwargs):
        kwargs = du.defaults(kwargs, {
            'left_data': self.data_map[0],
            'left_data_id': 0,
            'left_camera_pose': tf.Transform(location=(1, 2, 3),
                                             rotation=(4, 5, 6, 7)),
            'left_depth_data': self.data_map[1],
            'left_depth_id': 1,
            'left_labels_data': self.data_map[2],
            'left_labels_id': 2,
            'left_world_normals_data': self.data_map[3],
            'left_world_normals_id': 3,
            'right_data': self.data_map[4],
            'right_data_id': 4,
            'right_camera_pose': tf.Transform(location=(8, 9, 10),
                                              rotation=(11, 12, 13, 14)),
            'right_depth_data': self.data_map[5],
            'right_depth_id': 5,
            'right_labels_data': self.data_map[6],
            'right_labels_id': 6,
            'right_world_normals_data': self.data_map[7],
            'right_world_normals_id': 7,
            'metadata': imeta.ImageMetadata(
                source_type=imeta.ImageSourceType.SYNTHETIC,
                environment_type=imeta.EnvironmentType.INDOOR_CLOSE,
                light_level=imeta.LightingLevel.WELL_LIT,
                time_of_day=imeta.TimeOfDay.DAY,
                height=600,
                width=800,
                fov=90,
                focal_length=5,
                aperture=22,
                simulation_world='TestSimulationWorld',
                lighting_model=imeta.LightingModel.LIT,
                texture_mipmap_bias=1,
                normal_mipmap_bias=2,
                roughness_enabled=True,
                geometry_decimation=0.8,
                procedural_generation_seed=16234,
                label_classes=['cup', 'car', 'cow'],
                label_bounding_boxes={imeta.BoundingBox(class_name='cup', confidence=1,
                                                        x=10, y=65, height=24, width=39)},
                distances_to_labelled_objects={'cup': 1.223, 'car': 15.9887, 'cow': 102.63},
                average_scene_depth=90.12),
            'additional_metadata': {
                'Source': 'Generated',
                'Resolution': {'width': 1280, 'height': 720},
                'Material Properties': {
                    'BaseMipMapBias': 0,
                    'RoughnessQuality': True
                }
            }
        })
        return ie.StereoImageEntity(*args, **kwargs)

    def create_mock_db_client(self):
        self.db_client = super().create_mock_db_client()

        self.db_client.grid_fs = unittest.mock.create_autospec(gridfs.GridFS)
        self.db_client.grid_fs.get.side_effect = lambda id_: MockReadable(self.data_map[id_])

        return self.db_client

    def assert_models_equal(self, image1, image2):
        """
        Helper to assert that two stereo image entities are equal
        :param image1: StereoImageEntity
        :param image2: StereoImageEntity
        :return:
        """
        if not isinstance(image1, ie.StereoImageEntity) or not isinstance(image2, ie.StereoImageEntity):
            self.fail('object was not an StereoImageEntity')
        self.assertEqual(image1.identifier, image2.identifier)
        self.assertTrue(np.array_equal(image1.left_data, image2.left_data))
        self.assertTrue(np.array_equal(image1.right_data, image2.right_data))
        self.assertEqual(image1.left_camera_pose, image2.left_camera_pose)
        self.assertEqual(image1.right_camera_pose, image2.right_camera_pose)
        self.assertTrue(np.array_equal(image1.left_depth_data, image2.left_depth_data))
        self.assertTrue(np.array_equal(image1.left_labels_data, image2.left_labels_data))
        self.assertTrue(np.array_equal(image1.left_world_normals_data, image2.left_world_normals_data))
        self.assertTrue(np.array_equal(image1.right_depth_data, image2.right_depth_data))
        self.assertTrue(np.array_equal(image1.right_labels_data, image2.right_labels_data))
        self.assertTrue(np.array_equal(image1.right_world_normals_data, image2.right_world_normals_data))
        self.assertEqual(image1.additional_metadata, image2.additional_metadata)

    def test_constructor_works_with_minimal_arguments(self):
        ie.StereoImageEntity(left_data=np.random.randint(0, 255, (256, 256, 3), dtype='uint8'),
                             right_data=np.random.randint(0, 255, (256, 256, 3), dtype='uint8'),
                             left_camera_pose=tf.Transform(),
                             right_camera_pose=tf.Transform(),
                             metadata=imeta.ImageMetadata(
                                 source_type=imeta.ImageSourceType.SYNTHETIC,
                                 height=600,
                                 width=800
                             ))

    def test_serialize_and_deserialize_work_with_minimal_arguments(self):
        entity1 = ie.StereoImageEntity(left_data=self.data_map[0],
                                       left_data_id=0,
                                       right_data=self.data_map[1],
                                       right_data_id=1,
                                       left_camera_pose=tf.Transform(),
                                       right_camera_pose=tf.Transform(),
                                       metadata=imeta.ImageMetadata(
                                           source_type=imeta.ImageSourceType.SYNTHETIC,
                                           height=600,
                                           width=800
                                       ))
        s_entity = entity1.serialize()
        entity2 = ie.StereoImageEntity.deserialize(s_entity, self.create_mock_db_client())
        s_entity2 = entity2.serialize()
        self.assert_models_equal(entity1, entity2)
        self.assert_serialized_equal(s_entity, s_entity2)

    def test_deserialise_calls_gridfs(self):
        mock_db_client = self.create_mock_db_client()
        EntityClass = self.get_class()
        entity = self.make_instance(id_=12345)
        s_entity = entity.serialize()

        self.assertFalse(mock_db_client.grid_fs.get.called)
        EntityClass.deserialize(s_entity, mock_db_client)
        self.assertTrue(mock_db_client.grid_fs.get.called)
        self.assertEqual(8, mock_db_client.grid_fs.get.call_count)
        self.assertIn(mock.call(s_entity['left_data']), mock_db_client.grid_fs.get.call_args_list)
        self.assertIn(mock.call(s_entity['left_depth_data']), mock_db_client.grid_fs.get.call_args_list)
        self.assertIn(mock.call(s_entity['left_labels_data']), mock_db_client.grid_fs.get.call_args_list)
        self.assertIn(mock.call(s_entity['left_world_normals_data']), mock_db_client.grid_fs.get.call_args_list)

        self.assertIn(mock.call(s_entity['right_data']), mock_db_client.grid_fs.get.call_args_list)
        self.assertIn(mock.call(s_entity['right_depth_data']), mock_db_client.grid_fs.get.call_args_list)
        self.assertIn(mock.call(s_entity['right_labels_data']), mock_db_client.grid_fs.get.call_args_list)
        self.assertIn(mock.call(s_entity['right_world_normals_data']), mock_db_client.grid_fs.get.call_args_list)

    def test_does_not_deserialize_from_null_id(self):
        mock_db_client = self.create_mock_db_client()
        EntityClass = self.get_class()
        entity = self.make_instance(id_=12345)
        s_entity = entity.serialize()
        s_entity['left_depth_data'] = None
        s_entity['left_labels_data'] = None
        s_entity['left_world_normals_data'] = None
        s_entity['right_depth_data'] = None
        s_entity['right_labels_data'] = None
        s_entity['right_world_normals_data'] = None

        self.assertFalse(mock_db_client.grid_fs.get.called)
        EntityClass.deserialize(s_entity, mock_db_client)
        self.assertEqual(2, mock_db_client.grid_fs.get.call_count)

    def test_save_image_data_stores_in_gridfs(self):
        mock_db_client = self.create_mock_db_client()
        entity = self.make_instance(left_data_id=None,
                                    left_depth_id=None,
                                    left_labels_id=None,
                                    left_world_normals_id=None,
                                    right_data_id=None,
                                    right_depth_id=None,
                                    right_labels_id=None,
                                    right_world_normals_id=None)
        entity.save_image_data(mock_db_client)
        self.assertTrue(mock_db_client.grid_fs.put.called)
        self.assertEqual(8, mock_db_client.grid_fs.put.call_count)

    def test_save_image_data_does_not_store_data_if_already_stored(self):
        mock_db_client = self.create_mock_db_client()
        entity = self.make_instance()
        entity.save_image_data(mock_db_client, force_update=False)
        self.assertFalse(mock_db_client.grid_fs.put.called)

    def test_save_image_data_updates_ids(self):
        mock_db_client = self.create_mock_db_client()
        entity = self.make_instance(left_data_id=None,
                                    left_depth_id=None,
                                    left_labels_id=None,
                                    left_world_normals_id=None,
                                    right_data_id=None,
                                    right_depth_id=None,
                                    right_labels_id=None,
                                    right_world_normals_id=None)
        ids = [i for i in range(100, 900, 100)]  # the above ids are 0-3, these are definitely different
        mock_db_client.grid_fs.put.side_effect = ids
        entity.save_image_data(mock_db_client)
        s_entity = entity.serialize()
        self.assertIn(s_entity['left_data'], ids)
        self.assertIn(s_entity['left_depth_data'], ids)
        self.assertIn(s_entity['left_labels_data'], ids)
        self.assertIn(s_entity['left_world_normals_data'], ids)
        self.assertIn(s_entity['right_data'], ids)
        self.assertIn(s_entity['right_depth_data'], ids)
        self.assertIn(s_entity['right_labels_data'], ids)
        self.assertIn(s_entity['right_world_normals_data'], ids)


class TestImageToEntity(unittest.TestCase):

    def test_image_to_image_entity_does_nothing_to_an_image_entity(self):
        entity = ie.ImageEntity(data=np.random.randint(0, 255, (256, 256, 3), dtype='uint8'),
                                camera_pose=tf.Transform(),
                                metadata=imeta.ImageMetadata(
                                    source_type=imeta.ImageSourceType.SYNTHETIC,
                                    height=600,
                                    width=800
                                ))
        result = ie.image_to_entity(entity)
        self.assertEqual(entity, result)

    def test_image_to_image_entity_does_nothing_to_stereo_image_entity(self):
        entity = ie.StereoImageEntity(left_data=np.random.randint(0, 255, (256, 256, 3), dtype='uint8'),
                                      right_data=np.random.randint(0, 255, (256, 256, 3), dtype='uint8'),
                                      left_camera_pose=tf.Transform(),
                                      right_camera_pose=tf.Transform(),
                                      metadata=imeta.ImageMetadata(
                                          source_type=imeta.ImageSourceType.SYNTHETIC,
                                          height=600,
                                          width=800
                                      ))
        result = ie.image_to_entity(entity)
        self.assertEqual(entity, result)

    def test_image_to_image_entity_turns_image_to_image_entity(self):
        image = core.image.Image(data=np.random.randint(0, 255, (256, 256, 3), dtype='uint8'),
                                 camera_pose=tf.Transform(location=(10, 13, -67), rotation=(0.5, 0.1, 0.2)),
                                 metadata=imeta.ImageMetadata(
                                     source_type=imeta.ImageSourceType.SYNTHETIC,
                                     height=600,
                                     width=800
                                 ))
        entity = ie.image_to_entity(image)
        self.assertIsInstance(entity, ie.ImageEntity)
        self.assertTrue(np.array_equal(entity.data, image.data), "Image data are not equal")
        self.assertEqual(image.camera_pose, entity.camera_pose)

    def test_image_to_image_entity_turns_stereo_image_to_stereo_image_entity(self):
        image = core.image.StereoImage(left_data=np.random.randint(0, 255, (256, 256, 3), dtype='uint8'),
                                       right_data=np.random.randint(0, 255, (256, 256, 3), dtype='uint8'),
                                       left_camera_pose=tf.Transform(location=(10, 13, -67), rotation=(0.5, 0.1, 0.2)),
                                       right_camera_pose=tf.Transform(location=(-32, 2, -8), rotation=(0.1, 0.6, 0.8)),
                                       metadata=imeta.ImageMetadata(
                                           source_type=imeta.ImageSourceType.SYNTHETIC,
                                           height=600,
                                           width=800
                                       ))
        entity = ie.image_to_entity(image)
        self.assertIsInstance(entity, ie.StereoImageEntity)
        self.assertTrue(np.array_equal(entity.left_data, image.left_data), "Left image data are not equal")
        self.assertTrue(np.array_equal(entity.right_data, image.right_data), "Right image data are not equal")
        self.assertEqual(image.left_camera_pose, entity.left_camera_pose)
        self.assertEqual(image.right_camera_pose, entity.right_camera_pose)
