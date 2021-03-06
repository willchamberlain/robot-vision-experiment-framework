import logging
import logging.config
import traceback
import config.global_configuration as global_conf
import database.client
import util.database_helpers as dh
import batch_analysis.task_manager
import batch_analysis.job_systems.job_system_factory as job_system_factory


def main():
    """
    Schedule tasks for all experiments.
    We need to find a way of running this repeatedly as a daemon
    """
    config = global_conf.load_global_config('config.yml')
    logging.config.dictConfig(config['logging'])
    log = logging.getLogger(__name__)
    db_client = database.client.DatabaseClient(config=config)
    task_manager = batch_analysis.task_manager.TaskManager(db_client.tasks_collection, db_client)

    log.info("Scheduling experiments...")
    experiment_ids = db_client.experiments_collection.find({}, {'_id': True})
    for experiment_id in experiment_ids:
        experiment = dh.load_object(db_client, db_client.experiments_collection, experiment_id['_id'])
        if experiment is not None:
            # TODO: Separate scripts for scheduling and importing, they run at different rates
            try:
                experiment.do_imports(task_manager, db_client)
                experiment.schedule_tasks(task_manager, db_client)
                experiment.save_updates(db_client)
            except Exception:
                log.error("Exception occurred during scheduling:\n{0}".format(traceback.format_exc()))

    log.info("Scheduling tasks...")
    job_system = job_system_factory.create_job_system(config=config)
    task_manager.schedule_tasks(job_system)

    # Actually run the queued jobs.
    job_system.run_queued_jobs()

if __name__ == '__main__':
    main()
