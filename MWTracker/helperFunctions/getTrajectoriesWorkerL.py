# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 01:56:06 2015

@author: ajaver
"""
import os
import tables

from .. import config_param

from ..trackWorms.getWormTrajectories import getWormTrajectories, joinTrajectories
from ..trackWorms.getDrawTrajectories import drawTrajectoriesVideo
from ..trackWorms.getSkeletonsTables import trajectories2Skeletons, writeIndividualMovies
from ..trackWorms.checkHeadOrientation import correctHeadTail

from ..FeaturesAnalysis.obtainFeatures import getWormFeatures

from ..helperFunctions.tracker_param import tracker_param


checkpoint = {'TRAJ_CREATE':0, 'TRAJ_JOIN':1, 'TRAJ_VID':2, 
'SKE_CREATE':3, 'SKE_ORIENT':4, 'FEAT_CREATE':5, 'SKE_VIDEOS':6, 
 'END':1e6} 

checkpoint_label = {}
for key in checkpoint:
    checkpoint_label[checkpoint[key]] = key

    

def getStartingPoint(trajectories_file, skeletons_file, features_file):    
    '''determine for where to start. This is useful to check if the previous analysis was 
    completely succesfully, or if it was interrupted restarted from the last succesful step'''
    
    if not os.path.exists(trajectories_file):
        return checkpoint['TRAJ_CREATE'];
    else:
        try:
            with tables.open_file(trajectories_file, mode = 'r') as feature_fid:
                 feature_table = feature_fid.get_node('/plate_worms')
                 if feature_table._v_attrs['has_finished'] == 0:
                     return checkpoint['TRAJ_CREATE'];
                 elif feature_table._v_attrs['has_finished'] == 1:
                     return checkpoint['TRAJ_JOIN'];
        except:
            #if there is any problem while reading the file, create it again
            return checkpoint['TRAJ_CREATE'];
        
        
    if not os.path.exists(skeletons_file):
        return checkpoint['SKE_CREATE'];
    else:
        try:
            with tables.File(skeletons_file, "r") as ske_file_id:
                skeleton_table = ske_file_id.get_node('/skeleton')
                if skeleton_table._v_attrs['has_finished'] == 0:
                    return checkpoint['SKE_CREATE'];
                elif skeleton_table._v_attrs['has_finished'] == 1:
                    return checkpoint['SKE_ORIENT'];
        except:
            #if there is any problem while reading the file, create it again
            return checkpoint['SKE_CREATE'];
    
    if not os.path.exists(features_file):
        return checkpoint['FEAT_CREATE'];
    else:
        try:
            with tables.File(features_file, "r") as feat_file_id:
                features_table = feat_file_id.get_node('/Features_means')
                if features_table._v_attrs['has_finished'] == 0:
                    return checkpoint['FEAT_CREATE'];
        except:
            #if there is any problem while reading the file, create it again
            return checkpoint['FEAT_CREATE'];
    
        
    return checkpoint['END'];

def getTrajectoriesWorkerL(masked_image_file, results_dir, param_file ='', overwrite = False):
    
    #check if the file with the masked images exists
    assert os.path.exists(masked_image_file)
    
    if results_dir[-1] != os.sep:
        results_dir += os.sep
    if not os.path.exists(results_dir):
        try:
            os.makedirs(results_dir)
        except:
            pass
    
    #%%
    #get function parameters
    param = tracker_param(param_file)
    
    #%%
    #construct file names
    base_name = masked_image_file.rpartition('.')[0].rpartition(os.sep)[-1]
    
    trajectories_file = results_dir + base_name + '_trajectories.hdf5'
    skeletons_file = results_dir + base_name + '_skeletons.hdf5'
    features_file = results_dir + base_name + '_features.hdf5'
    
    #%%
    if overwrite:
        start_point = checkpoint['TRAJ_CREATE']
    else:
        start_point = getStartingPoint(trajectories_file, skeletons_file, features_file)

    print(base_name + ' Starting checkpoint: ' + checkpoint_label[start_point])

    #get trajectory data
    if start_point <= checkpoint['TRAJ_CREATE']:
        getWormTrajectories(masked_image_file, trajectories_file, **param.get_trajectories_param)
    
    if start_point <= checkpoint['TRAJ_JOIN']:        
        joinTrajectories(trajectories_file, **param.join_traj_param)

    #get skeletons data    
    if start_point <= checkpoint['SKE_CREATE']:
        trajectories2Skeletons(masked_image_file, skeletons_file, trajectories_file, **param.get_skeletons_param)

    if start_point <= checkpoint['SKE_ORIENT']:
        correctHeadTail(skeletons_file, **param.head_tail_param)
    
    if start_point <= checkpoint['FEAT_CREATE']:
        #extract features
        getWormFeatures(skeletons_file, features_file, **param.features_param)
    
    print(base_name + ' Finished')
    

    
    