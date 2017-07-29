import sys
import traceback
import bson.objectid

import config.global_configuration as global_conf
import database.client
import util.database_helpers as dh


def main(*args):
    """
    Train a trainee with a trainer.
    This represents a basic task.
    Scripts to run this will be autogenerated by the job system
    The first argument is the trainer ID, the second
    :return: void
    """
    if len(args) >= 2:
        trainer_id = bson.objectid.ObjectId(args[0])
        trainee_id = bson.objectid.ObjectId(args[1])
        experiment_id = bson.objectid.ObjectId(args[2]) if len(args) >= 3 else None

        config = global_conf.load_global_config('config.yml')
        db_client = database.client.DatabaseClient(config=config)

        trainer = dh.load_object(db_client, db_client.trainer_collection, trainer_id)
        trainee = dh.load_object(db_client, db_client.trainee_collection, trainee_id)
        experiment = dh.load_object(db_client, db_client.experiments_collection, experiment_id)

        success = False
        retry = True
        if trainer is not None and trainee is not None:
            if not trainer.can_train_trainee(trainee):
                retry = False
            else:
                try:
                    system = trainer.train_vision_system(trainee)
                except Exception:
                    traceback.print_exc()
                    system = None
                if system is not None:
                    system_id = db_client.system_collection.insert(system.serialize())
                    if experiment is not None:
                        experiment.add_system(trainer_id=trainer_id, trainee_id=trainee_id,
                                              system_id=system_id, db_client=db_client)
                        success = True
        if not success and experiment is not None:
            if retry:
                experiment.retry_training(trainer_id=trainer_id, trainee_id=trainee_id, db_client=db_client)
            else:
                experiment.mark_training_unsupported(trainer_id=trainer_id, trainee_id=trainee_id, db_client=db_client)


if __name__ == '__main__':
    main(*sys.argv[1:])
