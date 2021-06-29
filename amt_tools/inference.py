# Author: Frank Cwitkowitz <fcwitkow@ur.rochester.edu>

# My imports
from .transcribe import *
from . import tools

# Regular imports
import numpy as np
import argparse
import torch


def run_offline(track_data, model, estimator=None):
    """
    Perform inference in an offline fashion.

    Parameters
    ----------
    track_data : dict
      Dictionary containing relevant features for a track
    model : TranscriptionModel
      Model to use for inference
    estimator : Estimator
      Estimation protocol to use

    Returns
    ----------
    predictions : dict
      Dictionary containing predictions for a track
    """

    # Obtain the name of the track if it exists
    track_id = tools.unpack_dict(track_data, tools.KEY_TRACK)

    # Treat the track data as a batch
    track_data = tools.dict_unsqueeze(tools.dict_to_tensor(track_data))

    # Get the model predictions and convert them to NumPy arrays
    predictions = tools.dict_squeeze(tools.dict_to_array(model.run_on_batch(track_data)), dim=0)

    if estimator is not None:
        # Perform any estimation steps (e.g. note transcription)
        predictions.update(estimator.process_track(predictions, track_id))

    return predictions


def run_single_frame(track_data, model, predictions={}, estimator=None):
    """
    Perform inference on a single frame.

    Parameters
    ----------
    track_data : dict
      Dictionary containing relevant features for a track
    model : TranscriptionModel
      Model to use for inference
    predictions : dict
      Dictionary containing predictions for a track
    estimator : Estimator
      Estimation protocol to use

    Returns
    ----------
    predictions : dict
      Dictionary containing predictions for a track
    """

    # Obtain the name of the track if it exists
    track_id = tools.unpack_dict(track_data, tools.KEY_TRACK)

    # Make sure the track data and predictions consist of tensors
    # TODO - make sure these don't take much extra time
    track_data, predictions = tools.dict_to_tensor(track_data), tools.dict_to_tensor(predictions)

    # Run the frame group through the model
    new_predictions = tools.dict_squeeze(tools.dict_to_array(model.run_on_batch(track_data)), dim=0)

    if estimator is not None:
        # Perform any estimation steps (e.g. note transcription)
        new_predictions.update(estimator.process_track(new_predictions, track_id))

    # Append the results
    predictions = tools.dict_append(predictions, new_predictions)

    return predictions


def run_online(track_data, model, estimator=None):
    """
    Perform inference in an mock-online fashion.

    Parameters
    ----------
    track_data : dict
      Dictionary containing relevant features for a track
    model : TranscriptionModel
      Model to use for inference
    estimator : Estimator
      Estimation protocol to use

    Returns
    ----------
    predictions : dict
      Dictionary containing predictions for a track
    """

    # Obtain the features and times from the track data
    features = tools.unpack_dict(track_data, tools.KEY_FEATS)
    times = tools.unpack_dict(track_data, tools.KEY_TIMES)

    # Determine the number of frame groups to feed through the model
    num_frame_groups = features.shape[-1]

    # Window the features to mimic real-time operation
    features = tools.framify_activations(features, model.frame_width)
    # Convert the features to PyTorch tensor and add to device
    features = tools.array_to_tensor(features, model.device)

    # Initialize a dictionary to hold predictions
    predictions = {}

    # Feed the frame groups to the model one-at-a-time
    for i in range(num_frame_groups):
        # Treat the next frame groups as a batch of features
        batch = tools.dict_unsqueeze({tools.KEY_FEATS : features[..., i, :],
                                      tools.KEY_TIMES : times[..., i : i+1]})
        # Perform inference on a single frame
        predictions = run_single_frame(batch, model, predictions, estimator)

    return predictions
