import sys
import bson.objectid
import config.global_configuration as global_conf
import database.client


def main(*args):
    """
    Compare a trial result to a reference trial result.
    This represents a basic task.
    Scripts to run this will be autogenerated by the job system
    The first argument is the comparison benchmark,
    the second argument is the trial to compare, and the third argument is the reference trial id
    :return: 
    """
    if len(args) >= 3:
        benchmark_id = bson.objectid.ObjectId(args[0])
        comp_trial_id = bson.objectid.ObjectId(args[1])
        ref_trial_id = bson.objectid.ObjectId(args[2])

        config = global_conf.load_global_config('config.yml')
        db_client = database.client.DatabaseClient(config=config)

        s_benchmark = db_client.benchmarks_collection.find_one({'_id': benchmark_id})
        benchmark = db_client.deserialize_entity(s_benchmark)

        s_trial = db_client.trials_collection.find_one({'_id': comp_trial_id})
        comp_trial_result = db_client.deserialize_entity(s_trial)

        s_trial = db_client.trials_collection.find_one({'_id': ref_trial_id})
        ref_trial_result = db_client.deserialize_entity(s_trial)

        if benchmark.is_trial_appropriate(comp_trial_result) and benchmark.is_trial_appropriate(ref_trial_result):
            comparison_result = benchmark.compare_trial_results(comp_trial_result, ref_trial_result)
            db_client.results_collection.insert(comparison_result.serialize())


if __name__ == '__main__':
    main(*sys.argv[1:])