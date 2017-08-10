import os
import numpy as np
import re
import signal
import queue
import multiprocessing
import core.system
import core.sequence_type
import core.trial_result
import trials.slam.visual_slam
import util.transform as tf
import util.dict_utils as du


# Try and use LibYAML where available, fall back to the python implementation
from yaml import dump as yaml_dump
try:
    from yaml import CDumper as YamlDumper
except ImportError:
    from yaml import Dumper as YamlDumper


class ORBSLAM2(core.system.VisionSystem):
    """
    Python wrapper for ORB_SLAM2
    """

    def __init__(self, vocabulary_file, settings, temp_folder='temp', id_=None):
        super().__init__(id_=id_)
        self._vocabulary_file = vocabulary_file

        # Default settings based on UE4 calibration results
        self._orbslam_settings = du.defaults({}, settings, {
            'Camera': {
                # Camera calibration and distortion parameters (OpenCV)
                'fx': 928.1191957,
                'fy': 931.23612997,
                'cx': 480.38174413,
                'cy': 272.89477381,

                'k1': -0.1488979,
                'k2': 1.34554205,
                'p1': 0.00487404,
                'p2': 0.0040448,
                'k3': -2.98873439,

                # Camera frames per second
                'fps': 30.0,

                # Color order of the images (0: BGR, 1: RGB. It is ignored if images are grayscale)
                'RGB': 1,
            },
            'ORBextractor': {
                # ORB Extractor: Number of features per image
                'nFeatures': 2000,

                # ORB Extractor: Scale factor between levels in the scale pyramid
                'scaleFactor': 1.2,

                # ORB Extractor: Number of levels in the scale pyramid
                'nLevels': 8,

                # ORB Extractor: Fast threshold
                # Image is divided in a grid. At each cell FAST are extracted imposing a minimum response.
                # Firstly we impose iniThFAST. If no corners are detected we impose a lower value minThFAST
                # You can lower these values if your images have low contrast
                'iniThFAST': 20,
                'minThFAST': 7
            },
            # Viewer configuration expected by ORB_SLAM2
            'Viewer': {
                'KeyFrameSize': 0.05,
                'KeyFrameLineWidth': 1,
                'GraphLineWidth': 0.9,
                'PointSize': 2,
                'CameraSize': 0.08,
                'CameraLineWidth': 3,
                'ViewpointX': 0,
                'ViewpointY': -0.7,
                'ViewpointZ': -1.8,
                'ViewpointF': 500
            }
        })
        self._temp_folder = temp_folder

        self._expected_completion_timeout = 300     # This is how long we wait after the dataset is finished
        self._settings_file = None
        self._child_process = None
        self._input_queue = None
        self._output_queue = None
        self._gt_trajectory = None

    @property
    def is_deterministic(self):
        """
        Is the visual system deterministic.

        If this is false, it will have to be tested multiple times, because the performance will be inconsistent
        between runs.

        :return: True iff the algorithm will produce the same results each time.
        :rtype: bool
        """
        return False

    def is_image_source_appropriate(self, image_source):
        """
        Is the dataset appropriate for testing this vision system.
        :param image_source: The source for images that this system will potentially be run with.
        :return: True iff the particular dataset is appropriate for this vision system.
        :rtype: bool
        """
        return (image_source.sequence_type == core.sequence_type.ImageSequenceType.SEQUENTIAL and
                image_source.is_depth_available)

    def start_trial(self, sequence_type):
        """
        Start a trial with this system.
        After calling this, we can feed images to the system.
        When the trial is complete, call finish_trial to get the result.
        :param sequence_type: Are the provided images part of a sequence, or just unassociated pictures.
        :return: void
        """
        if sequence_type is not core.sequence_type.ImageSequenceType.SEQUENTIAL:
            return

        self.save_settings()  # we have to save the settings, so that orb-slam can load them
        self._gt_trajectory = {}
        self._input_queue = multiprocessing.Queue()
        self._output_queue = multiprocessing.Queue()
        self._child_process = multiprocessing.Process(target=run_orbslam,
                                                      args=(self._output_queue,
                                                            self._input_queue,
                                                            self._vocabulary_file,
                                                            self._settings_file))
        self._child_process.start()

    def process_image(self, image, timestamp):
        """
        Process an image as part of the current run.
        Should automatically start a new trial if none is currently started.
        :param image: The image object for this frame
        :param timestamp: A timestamp or index associated with this image. Sometimes None.
        :return: void
        """
        self._input_queue.put((np.copy(image.data), np.copy(image.depth_data), timestamp))

    def finish_trial(self):
        """
        End the current trial, returning a trial result.
        Return none if no trial is started.
        :return:
        :rtype TrialResult:
        """
        self._input_queue.put(None)
        try:
            trajectory_list, tracking_stats = self._output_queue.get(block=True,
                                                                     timeout=self._expected_completion_timeout)
        except queue.Empty:
            # process has failed to complete within expected time, kill it and move on.
            trajectory_list = None
            tracking_stats = []

        if isinstance(trajectory_list, list):
            # completed successfully, return the trajectory
            self._child_process.join()    # explicitly join

            trajectory = {}
            for timestamp, x, y, z, qx, qy, qz, qw in trajectory_list:
                # ORB_SLAM by default uses ROS coordinate frame, so we shouldn't need to convert
                trajectory[timestamp] = tf.Transform(location=(x, y, z),
                                                     rotation=(qw, qx, qy, qz), w_first=True)

            result = trials.slam.visual_slam.SLAMTrialResult(
                system_id=self.identifier,
                trajectory=trajectory,
                ground_truth_trajectory=self._gt_trajectory,
                tracking_stats=tracking_stats,
                sequence_type=core.sequence_type.ImageSequenceType.SEQUENTIAL,
                system_settings=self.get_settings()
            )
        else:
            # something went wrong, kill it with fire
            self._child_process.terminate()
            self._child_process.join(timeout=5)
            if self._child_process.is_alive():
                os.kill(self._child_process.pid, signal.SIGKILL)    # Definitely kill the process.
            result = core.trial_result.FailedTrial(
                system_id=self.identifier,
                reason="Child process timed out after {0} seconds.".format(self._expected_completion_timeout),
                sequence_type=core.sequence_type.ImageSequenceType.SEQUENTIAL,
                system_settings=self.get_settings()
            )

        if os.path.isfile(self._settings_file):
            os.remove(self._settings_file)  # Delete the settings file
        self._settings_file = None
        self._child_process = None
        self._input_queue = None
        self._output_queue = None
        self._gt_trajectory = None
        return result

    def get_settings(self):
        return self._orbslam_settings

    def save_settings(self):
        if self._settings_file is None:
            # Choose a new settings file
            self._settings_file = os.path.join(self._temp_folder, 'orb-slam2-settings-{0}'.format(
                self.identifier if self.identifier is not None else 'unregistered'))
            if os.path.isfile(self._settings_file):
                for idx in range(10000):
                    if not os.path.isfile(self._settings_file + '-' + str(idx)):
                        self._settings_file += '-' + str(idx)
            dump_config(self._settings_file, self._orbslam_settings)

    def serialize(self):
        serialized = super().serialize()
        serialized['vocabulary_file'] = self._vocabulary_file
        serialized['settings'] = self.get_settings()
        return serialized

    @classmethod
    def deserialize(cls, serialized_representation, db_client, **kwargs):
        if 'vocabulary_file' in serialized_representation:
            kwargs['vocabulary_file'] = serialized_representation['vocabulary_file']
        if 'settings' in serialized_representation:
            kwargs['settings'] = serialized_representation['settings']
        kwargs['temp_folder'] = db_client.temp_folder
        return super().deserialize(serialized_representation, db_client, **kwargs)


def load_config(filename):
    """
    Load an opencv yaml FileStorage file, accounting for a couple of inconsistencies in syntax.
    :param filename: The file to load from
    :return: A python object constructed from the config, or an empty dict if not found
    """
    config = {}
    with open(filename, 'r') as config_file:
        re_comment_split = re.compile('[%#]')
        for line in config_file:
            line = re_comment_split.split(line, 1)[0]
            if len(line) <= 0:
                continue
            else:
                key, value = line.split(':', 1)
                key = key.strip('"\' \t')
                value = value.strip()
                value_lower = value.lower()
                if value_lower == 'true':
                    actual_value = True
                elif value_lower == 'false':
                    actual_value = False
                else:
                    try:
                        actual_value = float(value)
                    except ValueError:
                        actual_value = value
                config[key] = actual_value
    return config


def dump_config(filename, data, dumper=YamlDumper, default_flow_style=False, **kwargs):
    """
    Dump the ORB_SLAM config to file,
    There's some fiddling with the format here so that OpenCV will read it on the other end.
    :param filename:
    :param data:
    :param dumper:
    :param default_flow_style:
    :param kwargs:
    :return:
    """
    with open(filename, 'w') as config_file:
        config_file.write("%YAML:1.0\n")
        return yaml_dump(data, config_file, Dumper=dumper, default_flow_style=default_flow_style, **kwargs)


def run_orbslam(output_queue, input_queue, vocab_file, settings_file):
    import orbslam2
    import trials.slam.tracking_state

    tracking_stats = []
    orbslam_system = orbslam2.System(vocab_file, settings_file)
    orbslam_system.set_use_viewer(True)
    orbslam_system.initialize()
    running = True

    while running:
        in_data = input_queue.get(block=True)
        if isinstance(in_data, tuple) and len(in_data) == 3:
            img_data, depth_data, timestamp = in_data

            orbslam_system.process_image(img_data, depth_data, timestamp)
            tracking_state = orbslam_system.get_tracking_state()
            if (tracking_state == orbslam2.TrackingState.SYSTEM_NOT_READY or
                    tracking_state == orbslam2.TrackingState.NO_IMAGES_YET or
                    tracking_state == orbslam2.TrackingState.NOT_INITIALIZED):
                tracking_stats.append(trials.slam.tracking_state.TrackingState.NOT_INITIALIZED)
            elif tracking_state == orbslam2.TrackingState.OK:
                tracking_stats.append(trials.slam.tracking_state.TrackingState.OK)
            else:
                tracking_stats.append(trials.slam.tracking_state.TrackingState.LOST)

    # send the final trajectory to the parent
    output_queue.put((orbslam_system.get_trajectory_points(), tracking_stats))

    # shut down the system. This is going to crash it, but that's ok, because it's a subprocess
    orbslam_system.shutdown()
