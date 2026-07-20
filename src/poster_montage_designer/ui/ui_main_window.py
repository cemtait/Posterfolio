# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMainWindow,
    QMenuBar, QPushButton, QSizePolicy, QSpacerItem,
    QStatusBar, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1200, 750)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.mainLayout = QHBoxLayout(self.centralwidget)
        self.mainLayout.setSpacing(1)
        self.mainLayout.setObjectName(u"mainLayout")
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.projectPanel = QWidget(self.centralwidget)
        self.projectPanel.setObjectName(u"projectPanel")
        self.projectPanel.setMinimumWidth(220)
        self.projectPanel.setMaximumWidth(280)
        self.projectLayout = QVBoxLayout(self.projectPanel)
        self.projectLayout.setSpacing(10)
        self.projectLayout.setObjectName(u"projectLayout")
        self.projectLayout.setContentsMargins(16, 16, 16, 16)
        self.projectTitleLabel = QLabel(self.projectPanel)
        self.projectTitleLabel.setObjectName(u"projectTitleLabel")

        self.projectLayout.addWidget(self.projectTitleLabel)

        self.newMontageButton = QPushButton(self.projectPanel)
        self.newMontageButton.setObjectName(u"newMontageButton")

        self.projectLayout.addWidget(self.newMontageButton)

        self.openMontageButton = QPushButton(self.projectPanel)
        self.openMontageButton.setObjectName(u"openMontageButton")

        self.projectLayout.addWidget(self.openMontageButton)

        self.projectStatusLabel = QLabel(self.projectPanel)
        self.projectStatusLabel.setObjectName(u"projectStatusLabel")
        self.projectStatusLabel.setWordWrap(True)

        self.projectLayout.addWidget(self.projectStatusLabel)

        self.projectSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.projectLayout.addItem(self.projectSpacer)


        self.mainLayout.addWidget(self.projectPanel)

        self.canvasPanel = QWidget(self.centralwidget)
        self.canvasPanel.setObjectName(u"canvasPanel")
        self.canvasLayout = QVBoxLayout(self.canvasPanel)
        self.canvasLayout.setObjectName(u"canvasLayout")
        self.canvasLayout.setContentsMargins(0, 0, 0, 0)
        self.canvasPlaceholderLabel = QLabel(self.canvasPanel)
        self.canvasPlaceholderLabel.setObjectName(u"canvasPlaceholderLabel")
        self.canvasPlaceholderLabel.setAlignment(Qt.AlignCenter)

        self.canvasLayout.addWidget(self.canvasPlaceholderLabel)


        self.mainLayout.addWidget(self.canvasPanel)

        self.propertiesPanel = QWidget(self.centralwidget)
        self.propertiesPanel.setObjectName(u"propertiesPanel")
        self.propertiesPanel.setMinimumWidth(260)
        self.propertiesPanel.setMaximumWidth(340)
        self.propertiesLayout = QVBoxLayout(self.propertiesPanel)
        self.propertiesLayout.setObjectName(u"propertiesLayout")
        self.propertiesLayout.setContentsMargins(16, 16, 16, 16)
        self.propertiesTitleLabel = QLabel(self.propertiesPanel)
        self.propertiesTitleLabel.setObjectName(u"propertiesTitleLabel")

        self.propertiesLayout.addWidget(self.propertiesTitleLabel)

        self.propertiesStatusLabel = QLabel(self.propertiesPanel)
        self.propertiesStatusLabel.setObjectName(u"propertiesStatusLabel")

        self.propertiesLayout.addWidget(self.propertiesStatusLabel)

        self.propertiesSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.propertiesLayout.addItem(self.propertiesSpacer)


        self.mainLayout.addWidget(self.propertiesPanel)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Poster Montage Designer", None))
        self.projectTitleLabel.setText(QCoreApplication.translate("MainWindow", u"Project", None))
        self.newMontageButton.setText(QCoreApplication.translate("MainWindow", u"New Montage...", None))
        self.openMontageButton.setText(QCoreApplication.translate("MainWindow", u"Open Montage...", None))
        self.projectStatusLabel.setText(QCoreApplication.translate("MainWindow", u"No project loaded.", None))
        self.canvasPlaceholderLabel.setText(QCoreApplication.translate("MainWindow", u"No montage open", None))
        self.propertiesTitleLabel.setText(QCoreApplication.translate("MainWindow", u"Properties", None))
        self.propertiesStatusLabel.setText(QCoreApplication.translate("MainWindow", u"Nothing selected.", None))
    # retranslateUi

