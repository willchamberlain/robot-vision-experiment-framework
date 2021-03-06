import unittest
import bson.objectid
import numpy as np

import database.tests.test_entity
import core.sequence_type
import trials.object_detection.bounding_box_result as bbox_result
import util.dict_utils as du


class TestBoundingBox(unittest.TestCase):

    def test_equals(self):
        kwargs = {
            'class_names': ('class_' + str(np.random.randint(255)),),
            'confidence': np.random.uniform(0, 0.8),
            'x': np.random.randint(800),
            'y': np.random.randint(600),
            'width': np.random.randint(128),
            'height': np.random.randint(128)
        }
        a = bbox_result.BoundingBox(**kwargs)
        b = bbox_result.BoundingBox(**kwargs)
        self.assertEqual(a, b)
        b = bbox_result.BoundingBox(**du.defaults({'class_names': 'class_413'}, kwargs))
        self.assertNotEqual(a, b)
        b = bbox_result.BoundingBox(**du.defaults({'confidence': 0.9}, kwargs))
        self.assertNotEqual(a, b)
        b = bbox_result.BoundingBox(**du.defaults({'x': 1600}, kwargs))
        self.assertNotEqual(a, b)
        b = bbox_result.BoundingBox(**du.defaults({'y': 900}, kwargs))
        self.assertNotEqual(a, b)
        b = bbox_result.BoundingBox(**du.defaults({'width': 137}, kwargs))
        self.assertNotEqual(a, b)
        b = bbox_result.BoundingBox(**du.defaults({'height': 137}, kwargs))
        self.assertNotEqual(a, b)

    def test_hash(self):
        kwargs = {
            'class_names': ('class_' + str(np.random.randint(255)),),
            'confidence': np.random.uniform(0, 0.8),
            'x': np.random.randint(800),
            'y': np.random.randint(600),
            'width': np.random.randint(128),
            'height': np.random.randint(128)
        }
        a = bbox_result.BoundingBox(**kwargs)
        b = bbox_result.BoundingBox(**kwargs)
        self.assertEqual(hash(a), hash(b))
        b = bbox_result.BoundingBox(**du.defaults({'class_names': 'class_413'}, kwargs))
        self.assertNotEqual(hash(a), hash(b))
        b = bbox_result.BoundingBox(**du.defaults({'confidence': 0.9}, kwargs))
        self.assertNotEqual(hash(a), hash(b))
        b = bbox_result.BoundingBox(**du.defaults({'x': 1600}, kwargs))
        self.assertNotEqual(hash(a), hash(b))
        b = bbox_result.BoundingBox(**du.defaults({'y': 900}, kwargs))
        self.assertNotEqual(hash(a), hash(b))
        b = bbox_result.BoundingBox(**du.defaults({'width': 137}, kwargs))
        self.assertNotEqual(hash(a), hash(b))
        b = bbox_result.BoundingBox(**du.defaults({'height': 137}, kwargs))
        self.assertNotEqual(hash(a), hash(b))

    def test_set(self):
        a = bbox_result.BoundingBox(
            class_names=('class_' + str(np.random.randint(255)),),
            confidence=np.random.uniform(0, 1),
            x=np.random.randint(800),
            y=np.random.randint(600),
            width=np.random.randint(128),
            height=np.random.randint(128)
        )
        b = bbox_result.BoundingBox(
            class_names=('class_' + str(np.random.randint(255)),),
            confidence=np.random.uniform(0, 1),
            x=np.random.randint(800),
            y=np.random.randint(600),
            width=np.random.randint(128),
            height=np.random.randint(128)
        )
        c = bbox_result.BoundingBox(
            class_names=('class_' + str(np.random.randint(255)),),
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
        for _ in range(10):
            bbox1 = bbox_result.BoundingBox(
                class_names=('class_' + str(np.random.randint(255)),),
                confidence=np.random.uniform(0, 1),
                x=np.random.randint(800),
                y=np.random.randint(600),
                width=np.random.randint(128),
                height=np.random.randint(128)
            )
            s_bbox1 = bbox1.serialize()

            bbox2 = bbox_result.BoundingBox.deserialize(s_bbox1)
            s_bbox2 = bbox2.serialize()

            self.assertEqual(bbox1, bbox2)
            self.assertEqual(s_bbox1, s_bbox2)

            for idx in range(10):
                # Test that repeated serialization and deserialization does not degrade the information
                bbox2 = bbox_result.BoundingBox.deserialize(s_bbox2)
                s_bbox2 = bbox2.serialize()
                self.assertEqual(bbox1, bbox2)
                self.assertEqual(s_bbox1, s_bbox2)


class TestBoundingBoxResult(database.tests.test_entity.EntityContract, unittest.TestCase):

    def get_class(self):
        return bbox_result.BoundingBoxResult

    def make_instance(self, *args, **kwargs):
        kwargs = du.defaults(kwargs, {
            'system_id': np.random.randint(10, 20),
            'bounding_boxes': {
                bson.objectid.ObjectId(): tuple(
                    bbox_result.BoundingBox(
                        class_names=('class_' + str(np.random.randint(255)),),
                        confidence=np.random.uniform(0, 1),
                        x=np.random.randint(800),
                        y=np.random.randint(600),
                        width=np.random.randint(128),
                        height=np.random.randint(128)
                    )
                    for _ in range(np.random.randint(50)))
                for _ in range(100)
            },
            'ground_truth_bounding_boxes': {
                bson.objectid.ObjectId(): tuple(
                    bbox_result.BoundingBox(
                        class_names=('class_' + str(np.random.randint(255)),),
                        confidence=np.random.uniform(0, 1),
                        x=np.random.randint(800),
                        y=np.random.randint(600),
                        width=np.random.randint(128),
                        height=np.random.randint(128)
                    )
                    for _ in range(np.random.randint(50)))
                for _ in range(100)
            },
            'sequence_type': core.sequence_type.ImageSequenceType.NON_SEQUENTIAL,
            'system_settings': {
                'a': np.random.randint(20, 30)
            }
        })
        return bbox_result.BoundingBoxResult(*args, **kwargs)

    def assert_models_equal(self, trial_result1, trial_result2):
        """
        Helper to assert that two feature detector trial results models are equal
        :param trial_result1:
        :param trial_result2:
        :return:
        """
        if (not isinstance(trial_result1,  bbox_result.BoundingBoxResult) or
                not isinstance(trial_result2, bbox_result.BoundingBoxResult)):
            self.fail('object was not a BoundingBoxResult')
        self.assertEqual(trial_result1.identifier, trial_result2.identifier)
        self.assertEqual(trial_result1.system_id, trial_result2.system_id)
        self.assertEqual(trial_result1.success, trial_result2.success)
        self.assertEqual(trial_result1.sequence_type, trial_result2.sequence_type)
        # Automatic comparison of this dict is extraordinarily slow, we have to unpack it
        self._assert_bboxes_equal(trial_result1.bounding_boxes, trial_result2.bounding_boxes)
        self._assert_bboxes_equal(trial_result1.ground_truth_bounding_boxes, trial_result2.ground_truth_bounding_boxes)
        self.assertEqual(trial_result1.settings, trial_result2.settings)

    def assert_serialized_equal(self, s_model1, s_model2):
        self.assertEqual(len(s_model1), len(s_model2))
        self.assertEqual(set(s_model1.keys()), set(s_model2.keys()))
        for key in s_model1.keys():
            if key is not 'bounding_boxes' and key is not 'gt_bounding_boxes':
                self.assertEqual(s_model1[key], s_model2[key])

        # Special comparison for the bounding boxes, because they're sets, so we don't care about order
        for bbox_key in ('bounding_boxes', 'gt_bounding_boxes'):
            self.assertEqual(set(s_model1[bbox_key].keys()), set(s_model2[bbox_key].keys()))
            for key in s_model1[bbox_key].keys():
                bboxes1 = {bbox_result.BoundingBox.deserialize(s_bbox) for s_bbox in s_model1[bbox_key][key]}
                bboxes2 = {bbox_result.BoundingBox.deserialize(s_bbox) for s_bbox in s_model2[bbox_key][key]}
                self.assertEqual(bboxes1, bboxes2)

    def _assert_bboxes_equal(self, bboxes1, bboxes2):
        self.assertEqual(len(bboxes1), len(bboxes2))
        self.assertEqual(set(bboxes1.keys()), set(bboxes2.keys()))
        for key in bboxes1.keys():
            self.assertEqual(bboxes1[key], bboxes2[key])

    def test_identifier(self):
        trial_result = self.make_instance(id_=123)
        self.assertEqual(trial_result.identifier, 123)
