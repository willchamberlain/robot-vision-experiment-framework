import core.benchmark
import benchmarks.bounding_box_overlap.bounding_box_overlap_result as bbox_result


class BoundingBoxOverlapBenchmark(core.benchmark.Benchmark):
    """
    A simple benchmark for bounding boxes detected over images.
    Produces scores based on the area of overlap between the detected bounding box and the ground truth box.
    Precision is overlap / detected area
    Recall is overlap / ground truth area
    Final score is F1 score times detection confidence
    """

    def __init__(self, id_=None):
        """
        Create a new benchmark instance. No configuration.
        """
        super().__init__(id_=id_)

    def serialize(self):
        output = super().serialize()
        # output['initializing_is_lost'] = self._initializing_is_lost
        return output

    @classmethod
    def deserialize(cls, serialized_representation, db_client, **kwargs):
        # if 'initializing_is_lost' in serialized_representation:
        #    kwargs['initializing_is_lost'] = serialized_representation['initializing_is_lost']
        return super().deserialize(serialized_representation, db_client, **kwargs)

    @classmethod
    def get_trial_requirements(cls):
        return {'success': True, 'tracking_stats': {'$exists': True, '$ne': []}}

    def is_trial_appropriate(self, trial_result):
        return (hasattr(trial_result, 'identifier') and
                hasattr(trial_result, 'get_ground_truth_bounding_boxes') and
                hasattr(trial_result, 'get_bounding_boxes'))

    def benchmark_results(self, trial_result):
        """
        Benchmark bounding boxes against the ground truth object labels
        :param trial_result: The results of a particular trial
        :return:
        :rtype BenchmarkResult:
        """
        ground_truth_bboxes = trial_result.get_ground_truth_bounding_boxes()
        detected_bboxes = trial_result.get_bounding_boxes()

        results = {}
        for image_id in ground_truth_bboxes.keys():
            results[image_id] = [{
                'overlap': 0,
                'bounding_box_area': 0,
                'ground_truth_area': gt_bbox.height * gt_bbox.width,
                'confidence': 0,
                'bounding_box_classes': tuple(),
                'ground_truth_classes': gt_bbox.class_names
            } for gt_bbox in ground_truth_bboxes[image_id]]

            if image_id in detected_bboxes:

                potential_matches = [(compute_overlap(gt_bbox, bbox), gt_idx, idx)
                                     for gt_idx, gt_bbox in enumerate(ground_truth_bboxes[image_id])
                                     for idx, bbox in enumerate(detected_bboxes[image_id])]
                potential_matches.sort(reverse=True)

                gt_indexes = set(range(len(ground_truth_bboxes[image_id])))
                bbox_indexes = set(range(len(detected_bboxes[image_id])))
                for overlap, gt_idx, idx in potential_matches:
                    if overlap <= 0:
                        break
                    if idx in bbox_indexes and gt_idx in gt_indexes:
                        gt_indexes.remove(gt_idx)
                        bbox_indexes.remove(idx)

                        bbox = detected_bboxes[image_id][idx]

                        results[image_id][gt_idx]['overlap'] = overlap
                        results[image_id][gt_idx]['confidence'] = bbox.confidence
                        results[image_id][gt_idx]['bounding_box_area'] = bbox.width * bbox.height
                        results[image_id][gt_idx]['bounding_box_classes'] = bbox.class_names

                # Record results for additionally detected bboxes
                for bbox_index in bbox_indexes:
                    bbox = detected_bboxes[image_id][bbox_index]
                    results[image_id].append({
                        'overlap': 0,
                        'bounding_box_area': bbox.height * bbox.width,
                        'ground_truth_area': 0,
                        'confidence': bbox.confidence,
                        'bounding_box_classes': bbox.class_names,
                        'ground_truth_classes': tuple()
                    })

        return bbox_result.BoundingBoxOverlapBenchmarkResult(benchmark_id=self.identifier,
                                                             trial_result_id=trial_result.identifier,
                                                             overlaps=results,
                                                             settings={})


def compute_overlap(bbox1, bbox2):
    if set(bbox1.class_names).isdisjoint(bbox2.class_names):
        return 0
    overlap_x = max((bbox1.x, bbox2.x))
    overlap_y = max((bbox1.y, bbox2.y))
    overlap_upper_x = min((bbox1.x + bbox1.width, bbox2.x + bbox2.width))
    overlap_upper_y = min((bbox1.y + bbox1.height, bbox2.y + bbox2.height))
    return ((overlap_upper_x - overlap_x)*(overlap_upper_y - overlap_y)
            if overlap_upper_x > overlap_x and overlap_upper_y > overlap_y else 0)
