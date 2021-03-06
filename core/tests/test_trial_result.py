import unittest
import numpy as np
import database.tests.test_entity
import util.dict_utils as du
import core.sequence_type
import core.trial_result


class TestTrialResult(database.tests.test_entity.EntityContract, unittest.TestCase):

    def get_class(self):
        return core.trial_result.TrialResult

    def make_instance(self, *args, **kwargs):
        kwargs = du.defaults(kwargs, {
            'system_id': np.random.randint(10, 20),
            'success': bool(np.random.randint(0, 1)),
            'sequence_type': core.sequence_type.ImageSequenceType.SEQUENTIAL,
            'system_settings': {'a': np.random.randint(30, 40)}
        })
        return core.trial_result.TrialResult(*args, **kwargs)

    def assert_models_equal(self, trial_result1, trial_result2):
        """
        Helper to assert that two dataset models are equal
        :param trial_result1: Dataset
        :param trial_result2: Dataset
        :return:
        """
        if (not isinstance(trial_result1, core.trial_result.TrialResult) or
                not isinstance(trial_result2, core.trial_result.TrialResult)):
            self.fail('object was not a TrialResult')
        self.assertEqual(trial_result1.identifier, trial_result2.identifier)
        self.assertEqual(trial_result1.system_id, trial_result2.system_id)
        self.assertEqual(trial_result1.sequence_type, trial_result2.sequence_type)
        self.assertEqual(trial_result1.settings, trial_result2.settings)
        self.assertEqual(trial_result1.success, trial_result2.success)


class TestFailedTrialResult(database.tests.test_entity.EntityContract, unittest.TestCase):
    def get_class(self):
        return core.trial_result.FailedTrial

    def make_instance(self, *args, **kwargs):
        kwargs = du.defaults(kwargs, {
            'system_id': np.random.randint(10, 20),
            'success': bool(np.random.randint(0, 1)),
            'sequence_type': core.sequence_type.ImageSequenceType.NON_SEQUENTIAL,
            'system_settings': {'a': np.random.randint(30, 40)},
            'reason': str(np.random.uniform(-10000, 10000))
        })
        return core.trial_result.FailedTrial(*args, **kwargs)

    def assert_models_equal(self, trial_result1, trial_result2):
        """
        Helper to assert that two dataset models are equal
        :param trial_result1: Dataset
        :param trial_result2: Dataset
        :return:
        """
        if (not isinstance(trial_result1, core.trial_result.FailedTrial) or
                not isinstance(trial_result2, core.trial_result.FailedTrial)):
            self.fail('object was not a TrialResult')
        self.assertEqual(trial_result1.identifier, trial_result2.identifier)
        self.assertEqual(trial_result1.system_id, trial_result2.system_id)
        self.assertEqual(trial_result1.sequence_type, trial_result2.sequence_type)
        self.assertEqual(trial_result1.settings, trial_result2.settings)
        self.assertEqual(trial_result1.success, trial_result2.success)
        self.assertEqual(trial_result1.reason, trial_result2.reason)

    def test_always_failed(self):
        instance = self.make_instance(success=True)
        self.assertFalse(instance.success)
