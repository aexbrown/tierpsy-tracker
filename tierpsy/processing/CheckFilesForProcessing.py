# -*- coding: utf-8 -*-
"""
Created on Tue Jun  9 15:12:48 2015

@author: ajaver
"""

import multiprocessing as mp
import os
from functools import partial

from tierpsy.helper.misc import TimeCounter, print_cmd_list
from tierpsy.processing.AnalysisPoints import AnalysisPoints, init_analysis_point_lock
from tierpsy.processing.ProcessLocal import BATCH_SCRIPT_LOCAL
from tierpsy.processing.helper import create_script

BREAK_L = '*********************************************'


class CheckFilesForProcessing(object):
    def __init__(self, video_dir_root, mask_dir_root, 
                 results_dir_root, tmp_dir_root='', 
                 json_file='', analysis_checkpoints = [],
                  is_copy_video = True, 
                  copy_unfinished=True,
                  is_parallel_check=True):
        
        def _testFileExists(fname, type_str):
            if fname:
                fname =  os.path.abspath(fname)
                if not os.path.exists(fname):
                    raise FileNotFoundError('%s does not exist.' % fname)
            return fname
        
        def _makeDirIfNotExists(fname):
            if fname:
                fname =  os.path.abspath(fname)
                if not os.path.exists(fname):
                    os.makedirs(fname)
            return fname
        
        # checkings before accepting the data
        self.video_dir_root = _testFileExists(video_dir_root, 'Videos root directory')
        self.mask_dir_root = _makeDirIfNotExists(mask_dir_root)
        self.results_dir_root = _makeDirIfNotExists(results_dir_root)
        self.json_file = _testFileExists(json_file, 'Parameters json file')
        
        self.tmp_dir_root = _makeDirIfNotExists(tmp_dir_root)

        self.is_copy_video = is_copy_video
        self.copy_unfinished = copy_unfinished

        self.analysis_checkpoints = analysis_checkpoints
        self.filtered_files = {}
        self.is_parallel_check = is_parallel_check
    def _checkIndFile(self, video_file):
        '''Check the progress in the file.'''
        
        print(video_file)
        
        video_dir, video_file_name = os.path.split(video_file)
        subdir_path = self._getSubDirPath(video_dir, self.video_dir_root)
        
        mask_dir = os.path.join(self.mask_dir_root, subdir_path)
        results_dir = os.path.join(self.results_dir_root, subdir_path)
        
        ap_obj = AnalysisPoints(video_file, mask_dir, results_dir, self.json_file)
        unfinished_points = ap_obj.getUnfinishedPoints(self.analysis_checkpoints)
        
        if len(unfinished_points) == 0:
            msg = 'FINISHED_GOOD'
        else:
            unmet_requirements = ap_obj.hasRequirements(unfinished_points[0])
            if len(unmet_requirements) > 0:
                msg ='SOURCE_BAD'
                #print(self.analysis_checkpoints[0], unmet_requirements)
                #print(ap_obj.file_names['masked_image'])
            elif unfinished_points != self.analysis_checkpoints:
                msg =  'FINISHED_BAD'
            else:
                msg = 'SOURCE_GOOD'

        
        return msg, ap_obj, unfinished_points
    
    
    def _getSubDirPath(self, source_dir, source_root_dir):
        '''Generate the destination dir path keeping the same structure 
        as the source directory'''

        #if the source_root_dir is empty do not create a subdir_path
        if not source_root_dir:
            return ''

        subdir_path = source_dir.replace(source_root_dir, '')

        #TODO: What happends is there is MaskedVideos within the subdirectory 

        # consider the case the subdirectory is only a directory separation
        # character
        if subdir_path and subdir_path[0] == os.sep:
            subdir_path = subdir_path[1:] if len(subdir_path) > 1 else ''
        
        return subdir_path
    

    @property
    def summary_msg(self):
        msg_pairs = [
        ('SOURCE_GOOD', 'Unprocessed files.'),
        ('FINISHED_BAD', 'Files whose analysis is incompleted.'),
        ('SOURCE_BAD', 'Invalid source files.'), 
        ('FINISHED_GOOD', 'Files that were succesfully finished.')
        ]

        def _vals2str(val, msg):
            return '{}\t{}'.format(val, msg)

        msd_dat = [ _vals2str(len(self.filtered_files[key]), msg) for key, msg in msg_pairs]
        tot_proc_files = len(self.filtered_files['SOURCE_GOOD']) + len(self.filtered_files['FINISHED_BAD'])
        
        
        s_msg = [BREAK_L]
        s_msg += ['Analysis Summary']
        s_msg += [BREAK_L]
        s_msg += msd_dat
        s_msg += [BREAK_L]
        s_msg += [_vals2str(tot_proc_files, 'Total files to be processed.')]
        s_msg += [BREAK_L]
        
       
        s_msg = '\n'.join(s_msg)


        return s_msg


    def filterFiles(self, valid_files, print_cmd=False):
        # for ii, video_file in enumerate(valid_files):
        #     label, ap_obj, unfinished_points = self._checkIndFile(video_file)
        #     self.filtered_files[label].append((ap_obj, unfinished_points))
            
        #     if (ii % 10) == 0:


        progress_timer = TimeCounter('')
        
        n_batch = mp.cpu_count()
        if self.is_parallel_check:
            lock = mp.Lock()
            p = mp.Pool(n_batch, initializer=init_analysis_point_lock, initargs=(lock,))
        
        all_points = []
        tot_files = len(valid_files)
        for ii in range(0, tot_files, n_batch):
            dat = valid_files[ii:ii + n_batch]
            
            if self.is_parallel_check:
                res = list(p.map(self._checkIndFile, dat))
            else:
                res = list(map(self._checkIndFile, dat))
            
            all_points.append(res)
            n_files = len(dat)
            print('Checking file {} of {}. Total time: {}'.format(ii + n_files, 
                      tot_files, progress_timer.get_time_str()))
        all_points = sum(all_points, []) #flatten
        
        # intialize filtered files lists
        filtered_files_fields = (
            'SOURCE_GOOD',
            'SOURCE_BAD',
            'FINISHED_GOOD',
            'FINISHED_BAD',
            'EMPTY_ANALYSIS_LIST')
        self.filtered_files = {key: [] for key in filtered_files_fields}
        for label, ap_obj, unfinished_points in all_points:
            self.filtered_files[label].append((ap_obj, unfinished_points))

        print(BREAK_L)
        print('''Finished to check files.\nTotal time elapsed {}'''.format(progress_timer.get_time_str()))
        print(BREAK_L + '\n')

        cmd_list = self.getCMDlist()
        if print_cmd:
            #print the commands to be executed
            print(BREAK_L)
            print('Commands to be executed.')
            print(BREAK_L)
            print_cmd_list(cmd_list)
            print(BREAK_L + '\n')

        
        print(self.summary_msg)
        
        return cmd_list
    
    def _printUnmetReq(self):
        def _get_unmet_requirements(input_data):
            ap_obj, unfinished_points = input_data
            for requirement in ap_obj.unmet_requirements:
                if requirement in ap_obj.checkpoints:
                    fname = ap_obj.checkpoints[requirement]['provenance_file']
                else:
                    requirement = '{} : {}'.format(requirement, ap_obj.file_names['original_video'])


                return requirement

        #print(self.filtered_files['SOURCE_BAD'])
        msg_l = map(_get_unmet_requirements, self.filtered_files['SOURCE_BAD'])
        msg ='\n'.join(msg_l)
        
        print(msg)
        return msg


    def getCMDlist(self):
        A = map(self.generateIndCMD, self.filtered_files['SOURCE_GOOD'])
        B = map(self.generateIndCMD, self.filtered_files['FINISHED_BAD'])
        return list(B) + list(A)

    def generateIndCMD(self, input_d):
        good_ap_obj, unfinished_points = input_d

        subdir_path = self._getSubDirPath(
            os.path.dirname(good_ap_obj.video_file),
            self.video_dir_root)
        
        if self.tmp_dir_root:
            tmp_mask_dir = os.path.join(self.tmp_dir_root, 'MaskedVideos', subdir_path) 
            tmp_results_dir = os.path.join(self.tmp_dir_root, 'Results', subdir_path)
        else:
            tmp_mask_dir, tmp_results_dir = '', ''

        args = [good_ap_obj.video_file]
        argkws = {'masks_dir':good_ap_obj.masks_dir, 
                  'results_dir':good_ap_obj.results_dir,
                  'tmp_mask_dir':tmp_mask_dir, 
                  'tmp_results_dir':tmp_results_dir,
                  'json_file':self.json_file, 
                  'analysis_checkpoints': unfinished_points,#self.analysis_checkpoints,
                  'is_copy_video':self.is_copy_video,
                  'copy_unfinished':self.copy_unfinished}
        
        cmd = create_script(BATCH_SCRIPT_LOCAL, args, argkws)
        return cmd
