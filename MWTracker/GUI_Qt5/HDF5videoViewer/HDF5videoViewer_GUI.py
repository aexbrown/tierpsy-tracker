import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QGraphicsScene, QGraphicsPixmapItem
from PyQt5.QtCore import QDir, QTimer, Qt, QRectF
from PyQt5.QtGui import QPixmap, QImage

from MWTracker.GUI_Qt5.HDF5videoViewer.HDF5videoViewer_ui import Ui_ImageViewer

import tables
import os
import numpy as np

class HDF5videoViewer_GUI(QMainWindow):
    def __init__(self, ui = ''):
        super().__init__()

        # Set up the user interface from Designer.
        if not ui:
            self.ui = Ui_ImageViewer()
        else:
            self.ui = ui

        self.ui.setupUi(self)
        
        
        self.isPlay = False
        self.fid = -1
        self.image_group = -1
        self.videos_dir = ''
        
        self.h5path = self.ui.comboBox_h5path.itemText(0)
        
        self.ui.pushButton_video.clicked.connect(self.getVideoFile)
        
        self.ui.playButton.clicked.connect(self.playVideo)
        self.ui.imageSlider.sliderPressed.connect(self.imSldPressed)
        self.ui.imageSlider.sliderReleased.connect(self.imSldReleased)
        self.ui.imageSlider.valueChanged.connect(self.imSldChanged)
        
        self.ui.spinBox_frame.valueChanged.connect(self.updateFrameNumber)
        self.ui.doubleSpinBox_fps.valueChanged.connect(self.updateFPS)
        self.ui.spinBox_step.valueChanged.connect(self.updateFrameStep)
        
        self.ui.spinBox_step.valueChanged.connect(self.updateFrameStep)

        self.ui.comboBox_h5path.activated.connect(self.getImGroup)

        self.ui.pushButton_h5groups.clicked.connect(self.updateGroupNames)

        self.updateFPS()
        self.updateFrameStep()
        
        # SET UP RECURRING EVENTS
        self.timer = QTimer()
        self.timer.timeout.connect(self.getNextImage)

        #set a pixmap for the graphcis scene. This allow to zoom in the image.
        self.ui._scene = QGraphicsScene(self)
        self.ui.imageCanvas = QGraphicsPixmapItem()
        self.ui._scene.addItem(self.ui.imageCanvas)
        self.ui.mainGraphicsView.setScene(self.ui._scene)
        self._zoom = 0
        self.ui.mainGraphicsView.wheelEvent = self.zoomWheelEvent

        #let drag and drop a file into the canvas
        self.ui.lineEdit_video.setAcceptDrops(True)
        self.ui.lineEdit_video.dragEnterEvent = self.canvasDragEnterEvent
        self.ui.lineEdit_video.dropEvent = self.canvasFileDrop

    #zoom wheel
    def zoomWheelEvent(self, event):
        if not self.ui.imageCanvas.pixmap().isNull():
            numPixels = event.pixelDelta();
            numDegrees = event.angleDelta()/8;

            delta = numPixels if not numPixels.isNull() else numDegrees

            if delta.y() > 0:
                factor = 1.25
                self._zoom += 1
            else:
                factor = 0.8
                self._zoom -= 1
            if self._zoom > 0:
                self.ui.mainGraphicsView.scale(factor, factor)
            elif self._zoom == 0:
                self.zoomFitInView()
            else:
                self._zoom = 0

    def zoomFitInView(self):
        rect = QRectF(self.ui.imageCanvas.pixmap().rect())
        if not rect.isNull():
            unity = self.ui.mainGraphicsView.transform().mapRect(QRectF(0, 0, 1, 1))
            self.ui.mainGraphicsView.scale(1 / unity.width(), 1 / unity.height())
            viewrect = self.ui.mainGraphicsView.viewport().rect()
            scenerect = self.ui.mainGraphicsView.transform().mapRect(rect)
            factor = min(viewrect.width() / scenerect.width(),
                         viewrect.height() / scenerect.height())
            self.ui.mainGraphicsView.scale(factor, factor)
            self.ui.mainGraphicsView.centerOn(rect.center())
            self._zoom = 0

    #Scroller
    def imSldPressed(self):
        self.ui.imageSlider.setCursor(Qt.ClosedHandCursor)
    
    def imSldReleased(self):
        self.ui.imageSlider.setCursor(Qt.OpenHandCursor)

    def imSldChanged(self):
        if self.image_group != -1:
            self.frame_number = int(round((self.tot_frames-1)*self.ui.imageSlider.value()/100))
            self.ui.spinBox_frame.setValue(self.frame_number)
        
    #frame spin box
    def updateFrameNumber(self):
        self.frame_number = self.ui.spinBox_frame.value()
        progress = round(100*self.frame_number/self.tot_frames)
        if progress != self.ui.imageSlider.value():
            self.ui.imageSlider.setValue(progress)
        
        self.updateImage()

    #fps spin box
    def updateFPS(self):
        self.fps = self.ui.doubleSpinBox_fps.value()

    #frame steps spin box
    def updateFrameStep(self):
        self.frame_step = self.ui.spinBox_step.value()

    #Play Button
    def playVideo(self):
        if self.image_group == -1:
            return
        if not self.isPlay:
            self.startPlay()
        else:
            self.stopPlay()
    
    def startPlay(self):
        self.timer.start(round(1000/self.fps))
        self.isPlay = True
        self.ui.playButton.setText('Stop')
        self.ui.doubleSpinBox_fps.setEnabled(False)

    def stopPlay(self):
        self.timer.stop()
        self.isPlay = False
        self.ui.playButton.setText('Play')
        self.ui.doubleSpinBox_fps.setEnabled(True)

    #Function to get the new valid frame during video play
    def getNextImage(self):
        self.frame_number += self.frame_step
        if self.frame_number >= self.tot_frames:
            self.frame_number = self.tot_frames-1
            self.stopPlay()
        
        self.ui.spinBox_frame.setValue(self.frame_number)
        
    #update image: get the next frame_number, and resize it to fix in the GUI area
    def updateImage(self):
        if self.image_group == -1:
            return
        
        self.readImage()

        self.pixmap = QPixmap.fromImage(self.frame_qimg)
        self.ui.imageCanvas.setPixmap(self.pixmap);
    
    def readImage(self):
        dd = self.ui.mainGraphicsView.size()
        self.label_height = dd.height()
        self.label_width = dd.width()

        self.frame_img = self.image_group[self.frame_number,:,:];
        
        #equalize and cast if it is not uint8
        if self.frame_img.dtype != np.uint8:
            top = np.max(self.frame_img)
            bot = np.min(self.frame_img)

            self.frame_img = (self.frame_img-bot)*255./(top-bot)
            self.frame_img = np.round(self.frame_img).astype(np.uint8)
            
        self.frame_qimg = QImage(self.frame_img.data, 
            self.image_width, self.image_height, self.frame_img.strides[0], QImage.Format_Indexed8)
        self.frame_qimg = self.frame_qimg.convertToFormat(QImage.Format_RGB32, Qt.AutoColor)
        
        #self.frame_qimg = self.frame_qimg.scaled(self.label_width, self.label_height, Qt.KeepAspectRatio)
        
    #file dialog to the the hdf5 file
    def getVideoFile(self):
        vfilename, _ = QFileDialog.getOpenFileName(self, "Find HDF5 video file", 
        self.videos_dir, "HDF5 files (*.hdf5);; All files (*)")

        self.updateVideoFile(vfilename)
        
    def canvasDragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()
        
    def canvasFileDrop(self, e):
        for url in e.mimeData().urls():
            vfilename = url.toLocalFile()
            if os.path.isfile(vfilename):
                self.updateVideoFile(vfilename)

    def updateVideoFile(self, vfilename):
        #close the if there was another file opened before.
        if self.fid != -1:
            self.fid.close()
            self.ui.imageCanvas.setPixmap(QPixmap())

        self.vfilename = vfilename
        self.ui.lineEdit_video.setText(self.vfilename)
        self.videos_dir = self.vfilename.rpartition(os.sep)[0] + os.sep
        
        try:
            self.fid = tables.File(vfilename, 'r')
        except (IOError, tables.exceptions.HDF5ExtError):
            self.fid = -1
            self.image_group = -1
            QMessageBox.critical(self, '', "The selected file is not a valid .hdf5. Please select a valid file",
                    QMessageBox.Ok)
            return

        self.updateImGroup()

    def updateGroupNames(self):
        valid_groups = []
        for group in self.fid.walk_groups("/"):
            for array in self.fid.list_nodes(group, classname='Array'):
                if array.ndim == 3:
                    valid_groups.append(array._v_pathname)
        
        if not valid_groups:
            QMessageBox.critical(self, '', "No valid video groups were found. Dataset with three dimensions and uint8 data type. Closing file.",
                    QMessageBox.Ok)
            self.fid.close()
            self.image_group = -1
            self.ui.imageCanvas.setPixmap(QPixmap())
            return

        self.ui.comboBox_h5path.clear()
        for kk in valid_groups:
            self.ui.comboBox_h5path.addItem(kk)
        self.getImGroup(0)
        self.updateImage()

    def getImGroup(self, index):
        self.h5path = self.ui.comboBox_h5path.itemText(index)
        self.updateImGroup()

    #read a valid groupset from the hdf5
    def updateImGroup(self):
        if self.fid == -1:
            return

        #self.h5path = self.ui.comboBox_h5path.text()
        if not self.h5path in self.fid:
            self.ui.imageCanvas.setPixmap(QPixmap())
            self.image_group == -1
            QMessageBox.critical(self, 'The groupset path does not exist', "The groupset path does not exists. You must specify a valid groupset path",
                    QMessageBox.Ok)
            return

        self.image_group = self.fid.get_node(self.h5path)
        if len(self.image_group.shape) != 3:
            self.ui.imageCanvas.setPixmap(QPixmap())
            self.image_group == -1
            QMessageBox.critical(self, 'Invalid groupset', "Invalid groupset. The groupset must have three dimensions",
                    QMessageBox.Ok)

        self.tot_frames = self.image_group.shape[0]
        self.image_height = self.image_group.shape[1]
        self.image_width = self.image_group.shape[2]
            
        self.ui.spinBox_frame.setMaximum(self.tot_frames-1)

        self.frame_number = 0
        self.ui.spinBox_frame.setValue(self.frame_number)
        self.updateImage()
        self.zoomFitInView()
        

    def setFileName(self, filename):
        self.filename = filename
        self.ui.lineEdit.setText(filename)

    
    def resizeEvent(self, event):
        if self.fid != -1:
            self.updateImage()
    
    def keyPressEvent(self, event):
        key = event.key()
        
        #Duplicate the frame step size (speed) when pressed  > or .: 
        if key == 46 or key == 62:
            self.frame_step *= 2
            self.ui.spinBox_step.setValue(self.frame_step)

        #Half the frame step size (speed) when pressed: < or ,
        elif key == 44 or key == 60:
            self.frame_step //=2
            if self.frame_step<1:
                self.frame_step = 1
            self.ui.spinBox_step.setValue(self.frame_step)

        elif self.fid == -1:
            return
            
        #Move backwards when  are pressed
        elif key == Qt.Key_Left or key == 39:
            self.frame_number -= self.frame_step
            if self.frame_number<0:
                self.frame_number = 0
            self.ui.spinBox_frame.setValue(self.frame_number)
        
        #Move forward when  are pressed
        elif key == Qt.Key_Right or key == 92:
            self.frame_number += self.frame_step
            if self.frame_number >= self.tot_frames:
                self.frame_number = self.tot_frames-1
            self.ui.spinBox_frame.setValue(self.frame_number)

        else:
            QMainWindow.keyPressEvent(self, event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    ui = HDF5videoViewer_GUI()
    ui.show()
    
    sys.exit(app.exec_())