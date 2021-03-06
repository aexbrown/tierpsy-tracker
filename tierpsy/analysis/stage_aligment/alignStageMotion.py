# -*- coding: utf-8 -*-
"""
Created on Thu Feb 11 22:01:59 2016

@author: ajaver
"""

import os
import subprocess as sp
import tempfile
import numpy as np
import tables

from tierpsy.helper.misc import print_flush


def alignStageMotion(
        masked_image_file,
        skeletons_file,
        tmp_dir=os.path.expanduser('~/Tmp')):

    assert os.path.exists(masked_image_file)
    assert os.path.exists(skeletons_file)
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    base_name = os.path.split(masked_image_file)[1].partition('.hdf5')[0]
    # check if it was finished before
    # with tables.File(skeletons_file, 'r+') as fid:
    #     try:
    #         has_finished = fid.get_node('/stage_movement')._v_attrs['has_finished'][:]
    #     except (KeyError, IndexError, tables.exceptions.NoSuchNodeError):
    #         has_finished = 0
    # if has_finished > 0:
    #     print_flush('%s The stage motion was previously aligned.' % base_name)
    #     return

    # get the current to add as a matlab path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    start_cmd = ('matlab -nojvm -nosplash -nodisplay -nodesktop <').split()

    script_cmd = "addpath('{}'); " \
        "try, alignStageMotionSegwormFun('{}', '{}'); " \
        "catch ME, disp(getReport(ME)); " \
        "end; exit; "

    script_cmd = script_cmd.format(
        current_dir, masked_image_file, skeletons_file)

    # create temporary file to read as matlab script, works better than
    # passing a string in the command line.
    tmp_fid, tmp_script_file = tempfile.mkstemp(
        suffix='.m', dir=tmp_dir, text=True)
    with open(tmp_script_file, 'w') as fid:
        fid.write(script_cmd)

    matlab_cmd = start_cmd + [tmp_script_file]

    # call matlab and align the stage motion
    print_flush('%s Aligning Stage Motion.' % base_name)
    sp.call(matlab_cmd)
    print_flush('%s Alignment finished.' % base_name)

    # delete temporary file.
    os.close(tmp_fid)
    os.remove(tmp_script_file)

def isGoodStageAligment(skeletons_file):
    with tables.File(skeletons_file, 'r') as fid:
        try:
            good_aligment = fid.get_node('/stage_movement')._v_attrs['has_finished'][:]
            print(good_aligment)
        except (KeyError, IndexError, tables.exceptions.NoSuchNodeError):
            good_aligment = 0

        return good_aligment in [1, 2]

def _h_get_stage_inv(skeletons_file, timestamp):
    first_frame = timestamp[0]
    last_frame = timestamp[-1]

    with tables.File(skeletons_file, 'r') as fid:
        stage_vec_ori = fid.get_node('/stage_movement/stage_vec')[:]
        timestamp_ind = fid.get_node('/timestamp/raw')[:].astype(np.int)
        rotation_matrix = fid.get_node('/stage_movement')._v_attrs['rotation_matrix']
        microns_per_pixel_scale = fid.get_node('/stage_movement')._v_attrs['microns_per_pixel_scale']
        #2D to control for the scale vector directions
            
    # let's rotate the stage movement
    dd = np.sign(microns_per_pixel_scale)
    rotation_matrix_inv = np.dot(
        rotation_matrix * [(1, -1), (-1, 1)], [(dd[0], 0), (0, dd[1])])

    # adjust the stage_vec to match the timestamps in the skeletons
    good = (timestamp_ind >= first_frame) & (timestamp_ind <= last_frame)

    ind_ff = timestamp_ind[good] - first_frame
    stage_vec_ori = stage_vec_ori[good]

    stage_vec = np.full((timestamp.size, 2), np.nan)
    stage_vec[ind_ff, :] = stage_vec_ori
    # the negative symbole is to add the stage vector directly, instead of
    # substracting it.
    stage_vec_inv = -np.dot(rotation_matrix_inv, stage_vec.T).T


    return stage_vec_inv

if __name__ == '__main__':
    file_mask = '/Users/ajaver/Desktop/Videos/single_worm/agar_1/MaskedVideos/unc-7 (cb5) on food R_2010_09_10__12_27_57__4.hdf5'
    file_skel = file_mask.replace(
        'MaskedVideos',
        'Results').replace(
        '.hdf5',
        '_skeletons.hdf5')
    alignStageMotion(file_mask, file_skel)
