import copy
import glob
import json
import os.path

import numpy as np
import cv2
import xxhash

import core.image_entity
import core.sequence_type
import dataset.image_collection_builder
import dataset.generated.metadata_patch as metadata_patch
import metadata.image_metadata as imeta
import metadata.camera_intrinsics as intrins
import util.dict_utils as du
import util.unreal_transform as ue_tf


def generate_image_filename(base_path, filename_format, mappings, index_padding,
                            index, extension, stereo_pass=0, render_pass=''):
    """
    Generate a filename for a particular image.
    Has a surprising number of parameters
    :param base_path:
    :param filename_format:
    :param mappings:
    :param index_padding:
    :param index:
    :param extension:
    :param stereo_pass:
    :param render_pass:
    :return:
    """
    mappings = dict(mappings)
    mappings['frame'] = str(index).zfill(index_padding)
    mappings['stereopass'] = stereo_pass
    if len(render_pass) > 0:
        render_pass = '_' + render_pass
    return os.path.join(base_path, filename_format.format(**mappings) + render_pass + extension)


def read_image_file(filename):
    """
    Load an image file. Each image object may contain more than one image file.
    :param filename: The name of the file to load from
    :return:
    """
    if not os.path.isfile(filename):
        return None
    data = cv2.imread(filename)
    if data is not None and len(data.shape) >= 3 and data.shape[2] > 1:
        return data[:, :, ::-1]  # fix the channel order to RGB if we have a colour image
    return data


def parse_transform(location, rotation):
    """
    Construct a transform from a stored location and rotation.
    Handles changing the coordinate frame from Unreal space to a conventional coordinate frame.
    :param location: dict containing X, Y, and Z
    :param rotation: dict containing W, Z, Y, and Z
    :return: a Transform object, in a sane coordinate frame and scaled to meters
    """
    ue_camera_pose = ue_tf.UnrealTransform(location=(location['X'],
                                                     location['Y'],
                                                     location['Z']),
                                           rotation=ue_tf.quat2euler(
                                               w=rotation['W'],
                                               x=rotation['X'],
                                               y=rotation['Y'],
                                               z=rotation['Z'],
                                           ))
    return ue_tf.transform_from_unreal(ue_camera_pose)


def sanitize_additional_metadata(metadata):
    """
    A simple sanitization of some keys from the additional metadata.
    :param metadata:
    :return:
    """
    for ignored_key in {'Version', 'Camera Location', 'Camera Orientation'}:
        if ignored_key in metadata:
            del metadata[ignored_key]
    return metadata


def build_image_metadata(im_data, ground_truth_depth_data, camera_pose, metadata, right_camera_pose=None):
    """
    Construct an image metadata object from the reference images and a metadata dict.
    Should delete the keys it uses from the metadata, so that the remaining values are  'additional metadata'
    :param im_data: The image data
    :param ground_truth_depth_data: Ground-truth depth, if available.
    :param metadata: The metadata dict
    :param camera_pose: The camera pose
    :param right_camera_pose: The pose of the right stereo camera, if available
    :return:
    """

    # Calculate focal length from fov, np.pi / 4 (rad) = 90 / 2 (deg) = fov / 2
    # this is the horizontal field of view,
    focal_length = 1 / (2 * np.tan(np.pi / 4))

    # In unreal 4, field of view is whichever is the larger dimension
    # See: https://answers.unrealengine.com/questions/36550/perspective-camera-and-field-of-view.html
    if im_data.shape[1] > im_data.shape[0]:     # Wider than tall, fov is horizontal FOV
        camera_intrinsics = intrins.CameraIntrinsics(focal_length, focal_length * (im_data.shape[1] / im_data.shape[0]),
                                                     0.5, 0.5)
    else:    # Taller than wide, fov is vertical fov
        camera_intrinsics = intrins.CameraIntrinsics(focal_length * (im_data.shape[0] / im_data.shape[1]), focal_length,
                                                     0.5, 0.5)
    image_metadata = imeta.ImageMetadata(
        hash_=xxhash.xxh64(np.ascontiguousarray(im_data)).digest(),
        source_type=imeta.ImageSourceType.SYNTHETIC,
        height=im_data.shape[0],
        width=im_data.shape[1],
        camera_pose=camera_pose,
        right_camera_pose=right_camera_pose,
        environment_type=imeta.EnvironmentType.INDOOR,
        light_level=imeta.LightingLevel.EVENLY_LIT,
        time_of_day=imeta.TimeOfDay.DAY,
        intrinsics=camera_intrinsics,
        right_intrinsics=camera_intrinsics if right_camera_pose is not None else None,
        fov=np.pi / 2,     # checked, this is definitely 90 degrees in all generated data
        focal_distance=None,
        aperture=None,
        simulation_world=metadata['World Name'],
        lighting_model=imeta.LightingModel.LIT,
        texture_mipmap_bias=int(metadata['Material Properties']['BaseMipMapBias']),
        normal_maps_enabled=int(metadata['Material Properties']['NormalQuality']) != 0,
        roughness_enabled=int(metadata['Material Properties']['RoughnessQuality']) != 0,
        geometry_decimation=int(metadata['Geometry Detail']['Forced LOD level']),
        procedural_generation_seed=int(metadata['World Information']['Camera Path']['Path Generation']['Random Seed']),
        labelled_objects=[],
        average_scene_depth=np.mean(ground_truth_depth_data) if ground_truth_depth_data is not None else None
    )
    for key in {'World Name', 'Material Properties', 'Geometry Detail'}:
        del metadata[key]
    return image_metadata


def load_image_set(base_path, filename_format, mappings, index_padding, index, extension, stereo_pass):
    path_kwargs = {
        'base_path': base_path,
        'filename_format': filename_format,
        'mappings': mappings,
        'index_padding': index_padding,
        'index': index,
        'extension': extension,
        'stereo_pass': stereo_pass
    }
    image_data = read_image_file(generate_image_filename(**path_kwargs))
    depth_data = read_image_file(generate_image_filename(render_pass='SceneDepthWorldUnits', **path_kwargs))
    labels_data = read_image_file(generate_image_filename(render_pass='ObjectMask', **path_kwargs))
    world_normals_data = read_image_file(generate_image_filename(render_pass='WorldNormals', **path_kwargs))
    return image_data, depth_data, labels_data, world_normals_data


def import_image_object(base_path, filename_format, mappings, index_padding,
                        index, extension, dataset_metadata):
    """
    Save an image to the database.
    First, assemble the ImageEntity from multiple image files, and a metadata file.
    Then, check if a similar image already exists in the database, if so, return that id.
    Otherwise, add the new Entity to the database, and return ID of the newly stored object.

    :param base_path: The base directory containing the image
    :param index: The index of the image, used in the filename
    :param filename_format: Additional formatting for the image filenames.
    :param mappings: Additional mappings fed to the filename generation
    :param index_padding: Padding to the index when creating the filename
    :param extension: The file extension
    :param dataset_metadata: Additional metadata held at the dataset level.
    :return: The ID of the newly loaded image, or None if it failed to load.
    :rtype bson.objectid.ObjectId:
    """
    # Rather than writing these out every time, create a kwargs object
    path_kwargs = {
        'base_path': base_path,
        'filename_format': filename_format,
        'mappings': mappings,
        'index_padding': index_padding,
        'index': index,
        'extension': extension
    }
    image_filename = generate_image_filename(stereo_pass=0, **path_kwargs)
    image_metadata_filename = image_filename + ".metadata.json"
    if not os.path.isfile(image_filename) or not os.path.isfile(image_metadata_filename):
        return None

    # Read the metadata file first
    with open(image_metadata_filename) as metadataFile:
        metadata = json.load(metadataFile)
    metadata_patch.update_image_metadata(metadata)

    # Read and transform the camera pose from the metadata file
    camera_pose = parse_transform(metadata['Camera Location'], metadata['Camera Orientation'])

    # Load the image files, will be None if they don't exist
    image_data = read_image_file(image_filename)
    if image_data is None:
        # Base image was none when we didn't expect it, fail loading this image.
        return None
    ground_truth_depth_data = read_image_file(generate_image_filename(stereo_pass=0, render_pass='SceneDepthWorldUnits',
                                                                      **path_kwargs))
    # TODO: Need to check these render pass names
    labels_data = read_image_file(generate_image_filename(stereo_pass=0, render_pass='ObjectMask', **path_kwargs))
    world_normals_data = read_image_file(generate_image_filename(stereo_pass=0, render_pass='WorldNormals',
                                                                 **path_kwargs))

    # Check if this is a stereo image.
    right_image_filename = generate_image_filename(stereo_pass=1, **path_kwargs)
    if not os.path.isfile(right_image_filename):
        # No right image, this is a monocular image, make the entity
        du.defaults(metadata, dataset_metadata)

        return core.image_entity.ImageEntity(
            data=image_data,
            metadata=build_image_metadata(image_data, ground_truth_depth_data, camera_pose, metadata),
            additional_metadata=sanitize_additional_metadata(metadata),
            ground_truth_depth_data=ground_truth_depth_data,
            labels_data=labels_data,
            world_normals_data=world_normals_data
        )
    else:
        # This is a stereo image, load the second image, then combine them into a StereoImageEntity
        with open(right_image_filename + ".metadata.json") as metadataFile:
            right_metadata = json.load(metadataFile)
        metadata_patch.update_image_metadata(right_metadata)

        # Read and transform the camera pose.
        right_camera_pose = parse_transform(right_metadata['Camera Location'], right_metadata['Camera Orientation'])

        # Read the component images
        right_image_data = read_image_file(right_image_filename)
        right_ground_truth_depth_data = read_image_file(generate_image_filename(stereo_pass=1,
                                                                                render_pass='SceneDepthWorldUnits',
                                                                                **path_kwargs))
        # TODO: Need to check these render pass names
        right_labels_data = read_image_file(generate_image_filename(stereo_pass=1, render_pass='ObjectMask',
                                                                    **path_kwargs))
        right_world_normals_data = read_image_file(generate_image_filename(stereo_pass=1, render_pass='WorldNormals',
                                                                           **path_kwargs))

        du.defaults(metadata, right_metadata, dataset_metadata)
        return core.image_entity.StereoImageEntity(
            metadata=build_image_metadata(image_data, ground_truth_depth_data, camera_pose,
                                          metadata, right_camera_pose),
            additional_metadata=sanitize_additional_metadata(metadata),
            left_data=image_data,
            left_ground_truth_depth_data=ground_truth_depth_data,
            left_labels_data=labels_data,
            left_world_normals_data=world_normals_data,
            right_data=right_image_data,
            right_ground_truth_depth_data=right_ground_truth_depth_data,
            right_labels_data=right_labels_data,
            right_world_normals_data=right_world_normals_data
        )


def import_dataset(metadata_path, db_client):
    """
    Search in a given folder path for generated image datasets and import them.
    A dataset is structured as a folder full of images, containing a file called 'metadata.json'
    The metadata contains information about how the images are named.
    All images must be indexed, determining their order in the image sequence.
    Uses iglob to search subdirectories, so it can import many datasets at once.

    :param metadata_path: The
    :param db_client: The client to the database to store the images in.
    :return: The ids of the newly imported datasets
    """
    if os.path.isfile(metadata_path):
        # Load the dataset
        with open(metadata_path, 'rU') as metadata_file:
            metadata = json.load(metadata_file)
        metadata_patch.update_dataset_metadata(metadata)

        builder = dataset.image_collection_builder.ImageCollectionBuilder(db_client)

        # First, load the images.
        dataset_dir = os.path.dirname(metadata_path)
        file_extension = metadata['File Extension']

        # loop over the maximum possible number of images, should break before the end of this range
        for index in range(0, len(glob.glob(os.path.join(dataset_dir, '*' + file_extension)))):
            image = import_image_object(base_path=dataset_dir,
                                        index=index,
                                        filename_format=metadata['Image Filename Format'],
                                        mappings=metadata['Image Filename Format Mappings'],
                                        index_padding=metadata['Index Padding'],
                                        extension=file_extension,
                                        dataset_metadata=copy.deepcopy(metadata))
            if image is not None:
                builder.add_image(image)
            else:
                # This image failed to load, lets assume we've reached the maximum range of the dataset
                break

        return builder.save()
    return None
