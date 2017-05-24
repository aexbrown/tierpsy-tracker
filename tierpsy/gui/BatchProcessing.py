import os
import json

from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt

from tierpsy.processing.processMultipleFilesFun import processMultipleFilesFun, getResultsDir
from tierpsy.processing.batchProcHelperFunc import getDefaultSequence

from tierpsy.gui.AnalysisProgress import AnalysisProgress, WorkerFunQt
from tierpsy.gui.HDF5VideoPlayer import LineEditDragDrop
from tierpsy.gui.BatchProcessing_ui import Ui_BatchProcessing
from tierpsy.gui.GetAllParameters import ParamWidgetMapper

#get default parameters files
from tierpsy.helper.params import TrackerParams
from tierpsy import DFLT_PARAMS_FILES
from tierpsy.processing.ProcessMultipleFilesParser import proccess_args_dflt, proccess_args_info, process_valid_options
process_valid_options['json_file'] = [''] + DFLT_PARAMS_FILES

proccess_args_dflt['analysis_sequence'] = 'all'


class BatchProcessing_GUI(QMainWindow):

    def __init__(self):
        super(BatchProcessing_GUI, self).__init__()
        self.mask_files_dir = ''
        self.results_dir = ''
        self.videos_dir = ''


        self.ui = Ui_BatchProcessing()
        self.ui.setupUi(self)
        self.mapper = ParamWidgetMapper(self.ui,
                                        default_param=proccess_args_dflt,
                                        info_param=proccess_args_info, 
                                        valid_options=process_valid_options)

        self.ui.checkBox_txtFileList.stateChanged.connect(
            self.enableTxtFileListButton)
        self.ui.checkBox_tmpDir.stateChanged.connect(self.enableTmpDirButton)
        

        self.ui.pushButton_txtFileList.clicked.connect(self.getTxtFileList)
        self.ui.pushButton_paramFile.clicked.connect(self.getParamFile)
        self.ui.pushButton_videosDir.clicked.connect(self.getVideosDir)
        self.ui.pushButton_masksDir.clicked.connect(self.getMasksDir)
        self.ui.pushButton_resultsDir.clicked.connect(self.getResultsDir)
        self.ui.pushButton_tmpDir.clicked.connect(self.getTmpDir)
        self.ui.pushButton_start.clicked.connect(self.startAnalysis)

        
        
        self.ui.checkBox_tmpDir.setChecked(False)
        self.enableTxtFileListButton()
        self.ui.checkBox_tmpDir.setChecked(True)
        self.enableTmpDirButton()

        self.ui.p_analysis_sequence.currentIndexChanged.connect(self.changeSequence)

        LineEditDragDrop(
            self.ui.p_videos_list,
            self.updateTxtFileList,
            os.path.isfile)
        LineEditDragDrop(
            self.ui.p_video_dir_root,
            self.updateVideosDir,
            os.path.isdir)
        LineEditDragDrop(
            self.ui.p_mask_dir_root,
            self.updateMasksDir,
            os.path.isdir)
        LineEditDragDrop(
            self.ui.p_results_dir_root,
            self.updateResultsDir,
            os.path.isdir)
        LineEditDragDrop(
            self.ui.p_tmp_dir_root,
            self.updateTmpDir,
            os.path.isdir)

        LineEditDragDrop(
            self.ui.p_json_file,
            self.updateParamFile,
            os.path.isfile)

        
                
        
    def enableTxtFileListButton(self):
        is_enable = self.ui.checkBox_txtFileList.isChecked()
        self.ui.pushButton_txtFileList.setEnabled(is_enable)
        self.ui.p_videos_list.setEnabled(is_enable)
        self.ui.label_patternIn.setEnabled(not is_enable)
        self.ui.label_patternExc.setEnabled(not is_enable)
        self.ui.p_pattern_exclude.setEnabled(not is_enable)
        self.ui.p_pattern_include.setEnabled(not is_enable)

        if not is_enable:
            self.updateTxtFileList('')

    def getTxtFileList(self):
        videos_list, _ = QFileDialog.getOpenFileName(
            self, "Select a text file with a list of files to be analyzed.", '', "Text file (*.txt);;All files (*)")
        if os.path.isfile(videos_list):
            self.updateTxtFileList(videos_list)

    def updateTxtFileList(self, videos_list):
        self.videos_list = videos_list
        self.ui.p_videos_list.setText(videos_list)

    def enableTmpDirButton(self):
        is_enable = self.ui.checkBox_tmpDir.isChecked()
        self.ui.pushButton_tmpDir.setEnabled(is_enable)
        self.ui.p_tmp_dir_root.setEnabled(is_enable)

        tmp_dir_root = proccess_args_dflt['tmp_dir_root'] if is_enable else ''
        self.updateTmpDir(tmp_dir_root)

    def getTmpDir(self):
        tmp_dir_root = QFileDialog.getExistingDirectory(
            self,
            "Selects the directory where the hdf5 masked videos will be stored",
            self.tmp_dir_root)
        if tmp_dir_root:
            self.updateTmpDir(tmp_dir_root)

    def updateTmpDir(self, tmp_dir_root):
        self.tmp_dir_root = tmp_dir_root
        self.ui.p_tmp_dir_root.setText(self.tmp_dir_root)

    def changeSequence(self, index):
        analysis_sequence = self.mapper['analysis_sequence']
        if analysis_sequence == 'track':
            self.ui.pushButton_videosDir.setEnabled(False)
        else:
            self.ui.pushButton_videosDir.setEnabled(True)

        if analysis_sequence == 'compress':
            self.ui.pushButton_videosDir.setEnabled(False)
        else:
            self.ui.pushButton_videosDir.setEnabled(True)

    def getVideosDir(self):
        videos_dir = QFileDialog.getExistingDirectory(
            self,
            "Selects the directory where the original video files are stored.",
            self.videos_dir)
        if videos_dir:
            self.updateVideosDir(videos_dir)


    def updateVideosDir(self, videos_dir):
        self.videos_dir = videos_dir
        self.ui.p_video_dir_root.setText(self.videos_dir)

        if 'Worm_Videos' in videos_dir:
            mask_files_dir = videos_dir.replace('Worm_Videos', 'MaskedVideos')
        elif 'RawVideos' in videos_dir:
            mask_files_dir = videos_dir.replace('RawVideos', 'MaskedVideos')
        else:
            mask_files_dir = os.path.join(videos_dir, 'MaskedVideos')

        self.updateMasksDir(mask_files_dir)

    def getResultsDir(self):
        results_dir = QFileDialog.getExistingDirectory(
            self,
            "Selects the directory where the analysis results will be stored",
            self.results_dir)
        if results_dir:
            self.updateResultsDir(results_dir)

    def updateResultsDir(self, results_dir):
        self.results_dir = results_dir
        self.mapper['results_dir_root'] = self.results_dir
    def getMasksDir(self):
        mask_files_dir = QFileDialog.getExistingDirectory(
            self,
            "Selects the directory where the hdf5 masked videos will be stored",
            self.mask_files_dir)
        if mask_files_dir:
            self.updateMasksDir(mask_files_dir)

    def updateMasksDir(self, mask_files_dir):
        if 'MaskedVideos' in mask_files_dir:
            results_dir = mask_files_dir.replace('MaskedVideos', 'Results')
        else:
            results_dir = os.path.join(mask_files_dir, 'Results')


        self.mask_files_dir = mask_files_dir
        self.mapper['mask_dir_root'] = self.mask_files_dir
        
        self.updateResultsDir(results_dir)

    def getParamFile(self):
        param_file, _ = QFileDialog.getOpenFileName(
            self, "Find parameters file", '', "JSON files (*.json);; All (*)")
        if param_file:
            self.updateParamFile(param_file)

    def updateParamFile(self, param_file):
        # i accept a file if it is empty (the program will call default parameters),
        # but if not I want to check if it is a valid file.
        if param_file:
            try:
                with open(param_file, 'r') as fid:
                    json_str = fid.read()
                    json_param = json.loads(json_str)

                    #find the current index in the combobox, if it preappend it.
                    ind_comb = self.ui.p_json_file.findText(param_file)
                    if ind_comb == -1:
                        self.ui.p_json_file.insertItem(-1, param_file)
                        ind_comb = 0

                    self.ui.p_json_file.setCurrentIndex(ind_comb)


            except (IOError, OSError, UnicodeDecodeError, json.decoder.JSONDecodeError):
                QMessageBox.critical(
                    self,
                    'Cannot read parameters file.',
                    "Cannot read parameters file. Try another file",
                    QMessageBox.Ok)
                return

        self.param_file = param_file

    def startAnalysis(self):
        process_args = proccess_args_dflt.copy()
        #append the root dir if we are using any of the default parameters files. I didn't add the dir before because it is easy to read them in this way.
        param = TrackerParams(self.mapper['json_file'])
        analysis_sequence = self.mapper['analysis_sequence']
        analysis_checkpoints = getDefaultSequence(analysis_sequence, is_single_worm=param.is_single_worm)
        process_args['analysis_checkpoints'] : analysis_checkpoints
        
        for x in self.mapper:
            process_args[x] = self.mapper[x]


        if 'COMPRESS' in process_args['analysis_checkpoints']:
            if not os.path.exists(process_args['video_dir_root']):
                QMessageBox.critical(
                    self,
                    'Error',
                    "The videos directory does not exist. Please select a valid directory.",
                    QMessageBox.Ok)
                return
        elif not os.path.exists(process_args['mask_dir_root']):
            QMessageBox.critical(
                self,
                'Error',
                "The masks directory does not exist. Please select a valid directory.",
                QMessageBox.Ok)
            return


        analysis_worker = WorkerFunQt(processMultipleFilesFun, process_args)
        progress = AnalysisProgress(analysis_worker)
        progress.exec_()

    


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    ui = BatchProcessing_GUI()
    ui.show()
    sys.exit(app.exec_())
