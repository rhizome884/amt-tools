# My imports
from .common import TranscriptionDataset
from ..tools import *

# Regular imports
import numpy as np
import os

# TODO - put velocity to use
# TODO - significant overlap in load with MAESTRO


class MAPS(TranscriptionDataset):
    """
    Implements the MAPS piano transcription dataset
    (https://www.tsi.telecom-paristech.fr/aao/en/2010/07/08/
    maps-database-a-piano-database-for-multipitch-estimation-and-automatic-transcription-of-music/).
    """

    def __init__(self, base_dir=None, splits=None, hop_length=512, sample_rate=16000, data_proc=None, profile=None,
                 num_frames=None, split_notes=False, reset_data=False, store_data=True, save_data=True, seed=0):
        """
        Initialize the dataset and establish parameter defaults in function signature.

        Parameters
        ----------
        See TranscriptionDataset class...
        """

        super().__init__(base_dir, splits, hop_length, sample_rate, data_proc, profile,
                         num_frames, split_notes, reset_data, store_data, save_data, seed)

    def get_tracks(self, split):
        """
        Get the tracks associated with a dataset partition.

        Parameters
        ----------
        split : string
          Name of the partition from which to fetch tracks

        Returns
        ----------
        tracks : list of strings
          Names of tracks within the given partition
        """

        # Construct a path to the MAPS music piece directory
        split_dir = os.path.join(self.base_dir, split, 'MUS')
        # Extract the names of all the files in the directory
        split_paths = os.listdir(split_dir)

        # Remove the extensions (text, midi, audio), leaving three repeats per track
        tracks = [os.path.splitext(path)[0] for path in split_paths]
        # Collapse repeats by adding the extensionless file names to a set
        tracks = list(set(tracks))
        # Sort all of the tracks alphabetically
        tracks.sort()

        return tracks

    def load(self, track):
        """
        Load the ground-truth from memory or generate it from scratch.

        Parameters
        ----------
        track : string
          Name of the track to load

        Returns
        ----------
        data : dict
          Dictionary with ground-truth for the track
        """

        # Load the track data if it exists in memory, otherwise instantiate track data
        data = super().load(track)

        # If the track data is being instantiated, it will not have the 'audio' key
        if 'audio' not in data.keys():
            # Determine the piano used for the track (last part of track name)
            piano = track.split('_')[-1]
            # Construct a path to the directory containing pieces played on the piano
            track_dir = os.path.join(self.base_dir, piano, 'MUS')

            # Construct the path to the track's audio
            wav_path = os.path.join(track_dir, track + '.wav')
            # Load and normalize the audio
            audio, fs = load_audio(wav_path, self.sample_rate)
            # Add the audio and sampling rate to the track data
            data['audio'], data['fs'] = audio, fs

            # Construct the path to the track's MIDI data
            midi_path = os.path.join(track_dir, track + '.mid')
            # Load the notes from the MIDI data and remove the velocity
            notes = load_midi_notes(midi_path)[:, :-1]
            # Convert the note lists to a note array
            pitches, intervals = arr_to_note_groups(notes)

            # We need the frame times to convert from notes to frames
            times = self.data_proc.get_times(data['audio'])

            # Check which instrument profile is used
            if isinstance(self.profile, PianoProfile):
                # Decode the notes into pianoroll to obtain the frame-wise pitches
                pitch = midi_groups_to_pianoroll(pitches, intervals, times, self.profile.get_midi_range())
            else:
                raise AssertionError('Provided InstrumentProfile not supported...')

            # Add the frame-wise pitches to the track data
            data['pitch'] = pitch

            # Convert the note pitches to hertz
            notes[:, -1] = librosa.midi_to_hz(notes[:, -1])
            # Add the note array to the track data
            data['notes'] = notes

            if self.save_data:
                # Get the appropriate path for saving the track data
                gt_path = self.get_gt_dir(track)
                # Save the audio, sampling rate, frame-wise pitches, and notes
                np.savez(gt_path,
                         fs=fs,
                         audio=audio,
                         pitch=pitch,
                         notes=notes)

        return data

    def remove_overlapping(self, splits):
        """
        Remove any tracks contained in the given splits from
        the initial dataset partition, should they exist.

        Parameters
        ----------
        splits : list of strings
          Splits to check for repeat tracks
        """

        tracks = []
        # Aggregate all the track names from the selected splits
        for split in splits:
            tracks += self.get_tracks(split)

        # Remove the piano from each track name
        tracks = ['_'.join(t.split('_')[:-1]) for t in tracks]
        # Rebuild the internal list of tracks with non-intersecting tracks
        self.tracks = [t for t in self.tracks if '_'.join(t.split('_')[:-1]) not in tracks]

        if self.store_data:
            # Loop through all internal ground-truth entries
            for key in list(self.data.keys()):
                # If the corresponding track entry no longer
                # exists, remove the ground-truth entry as well
                if key not in self.tracks:
                    self.data.pop(key)

    @staticmethod
    def available_splits():
        """
        Obtain a list of possible splits. Currently, the splits are by
        piano, in accordance with the default organization of the dataset.

        Returns
        ----------
        splits : list of strings
          Names of pianos used in MAPS
        """

        splits = ['AkPnBcht', 'AkPnBsdf', 'AkPnCGdD', 'AkPnStgb',
                  'ENSTDkAm', 'ENSTDkCl', 'SptkBGAm', 'SptkBGCl', 'StbgTGd2']

        return splits

    @staticmethod
    def download(save_dir):
        """
        Currently, this function stops execution. I am not aware of a way to
        automatically download MAPS. I will consider this again some time in
        the future.

        Parameters
        ----------
        save_dir : string
          Directory in which to save the contents of MAPS
        """

        # TODO

        assert False, 'MAPS must be requested and downloaded manually'
