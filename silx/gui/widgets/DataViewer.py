# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2016-2017 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ###########################################################################*/
"""This module defines a widget designed to display data using to most adapted
view from available ones from silx.
"""
from __future__ import division

__authors__ = ["V. Valls"]
__license__ = "MIT"
__date__ = "06/01/2017"

import numpy
import numbers

import silx.io
from silx.gui import qt
from silx.gui.widgets.NumpyAxesSelector import NumpyAxesSelector

try:
    from silx.third_party import six
except ImportError:
    import six


class DataView(object):
    """Holder for the data view."""

    def __init__(self, parent, modeId):
        """Constructor

        :param qt.QWidget parent: Parent of the hold widget
        """
        self.__parent = parent
        self.__widget = None
        self.__modeId = modeId

    def modeId(self):
        """Returns the mode id"""
        return self.__modeId

    def axiesNames(self):
        """Returns names of the expected axes of the view"""
        return []

    def getWidget(self):
        """Returns the widget hold in the view and displaying the data.

        :returns: qt.QWidget
        """
        if self.__widget is None:
            self.__widget = self.createWidget(self.__parent)
        return self.__widget

    def createWidget(self, parent):
        """Create the the widget displaying the data

        :param qt.QWidget parent: Parent of the widget
        :returns: qt.QWidget
        """
        raise NotImplementedError()

    def clear(self):
        """Clear the data from the view"""
        return None

    def setData(self, data):
        """Set the data displayed by the view

        :param data: Data to display
        :type data: numpy.ndarray or h5py.Dataset
        """
        return None

    def getDataPriority(self, data):
        """
        Returns the priority of using this view according to a data.

        - `-1` means this view can't display this data
        - `0` means this view can display the data if there is no other choices
        - `1` means this view can display the data
        - `100` means this view should be used for this data
        - ...

        :rtype: int
        """
        return -1

    def __lt__(self, other):
        return str(self) < str(other)


class _EmptyView(DataView):
    """Dummy view to display nothing"""

    def axiesNames(self):
        return []

    def createWidget(self, parent):
        return qt.QLabel(parent)

    def getDataPriority(self, data):
        return -1


class _Plot1dView(DataView):
    """View displaying data using a 1d plot"""

    def __init__(self, parent, modeId):
        super(_Plot1dView, self).__init__(parent, modeId)
        self.__resetZoomNextTime = True

    def axiesNames(self):
        return ["y"]

    def createWidget(self, parent):
        from silx.gui import plot
        return plot.Plot1D(parent=parent)

    def clear(self):
        self.getWidget().clear()
        self.__resetZoomNextTime = True

    def setData(self, data):
        self.getWidget().addCurve(legend="data",
                                  x=range(len(data)),
                                  y=data,
                                  resetzoom=self.__resetZoomNextTime)
        self.__resetZoomNextTime = False

    def getDataPriority(self, data):
        if data is None:
            return -1
        isArray = isinstance(data, numpy.ndarray)
        isArray = isArray or (silx.io.is_dataset(data) and data.shape != tuple())
        if not isArray:
            return -1
        isNumeric = numpy.issubdtype(data.dtype, numpy.number)
        if not isNumeric:
            return -1
        if len(data.shape) == 1:
            return 100
        else:
            return 10


class _Plot2dView(DataView):
    """View displaying data using a 2d plot"""

    def __init__(self, parent, modeId):
        super(_Plot2dView, self).__init__(parent, modeId)
        self.__resetZoomNextTime = True

    def axiesNames(self):
        return ["y", "x"]

    def createWidget(self, parent):
        from silx.gui import plot
        widget = plot.Plot2D(parent=parent)
        widget.setKeepDataAspectRatio(True)
        widget.setGraphXLabel('X')
        widget.setGraphYLabel('Y')
        return widget

    def clear(self):
        self.getWidget().clear()
        self.__resetZoomNextTime = True

    def setData(self, data):
        self.getWidget().addImage(legend="data",
                                  data=data,
                                  resetzoom=self.__resetZoomNextTime)
        self.__resetZoomNextTime = False

    def getDataPriority(self, data):
        if data is None:
            return -1
        isArray = isinstance(data, numpy.ndarray)
        isArray = isArray or (silx.io.is_dataset(data) and data.shape != tuple())
        if not isArray:
            return -1
        isNumeric = numpy.issubdtype(data.dtype, numpy.number)
        if not isNumeric:
            return -1
        if len(data.shape) < 2:
            return -1
        if len(data.shape) == 2:
            return 100
        else:
            return 10


class _ArrayView(DataView):
    """View displaying data using a 2d table"""

    def axiesNames(self):
        return ["col", "row"]

    def createWidget(self, parent):
        from silx.gui.widgets.ArrayTableWidget import ArrayTableWidget
        widget = ArrayTableWidget(parent)
        widget.displayAxesSelector(False)
        return widget

    def clear(self):
        self.getWidget().setArrayData(numpy.array([[]]))

    def setData(self, data):
        self.getWidget().setArrayData(data)

    def getDataPriority(self, data):
        if data is None:
            return -1
        isArray = isinstance(data, numpy.ndarray)
        isArray = isArray or (silx.io.is_dataset(data) and data.shape != tuple())
        if not isArray:
            return -1
        if len(data.shape) < 2:
            return -1
        return 50


class _TextView(DataView):
    """View displaying data using text"""

    __format = "%g"

    def axiesNames(self):
        return []

    def createWidget(self, parent):
        widget = qt.QTextEdit(parent)
        widget.setTextInteractionFlags(qt.Qt.TextSelectableByMouse)
        widget.setAlignment(qt.Qt.AlignLeft | qt.Qt.AlignTop)
        return widget

    def clear(self):
        self.getWidget().setText("")

    def toString(self, data):
        """Rendering a data into a readable string

        :param data: Data to render
        :rtype: str
        """
        if isinstance(data, (tuple, numpy.void)):
            text = [self.toString(d) for d in data]
            return "(" + " ".join(text) + ")"
        elif isinstance(data, (list, numpy.ndarray)):
            text = [self.toString(d) for d in data]
            return "[" + " ".join(text) + "]"
        elif isinstance(data, (numpy.string_, numpy.object_, bytes)):
            try:
                return "%s" % data.decode("utf-8")
            except UnicodeDecodeError:
                pass
            import binascii
            return "0x" + binascii.hexlify(data).decode("ascii")
        elif isinstance(data, six.string_types):
            return "%s" % data
        elif isinstance(data, numpy.complex_):
            if data.imag < 0:
                template = self.__format + " - " + self.__format + "j"
            else:
                template = self.__format + " + " + self.__format + "j"
            return template % (data.real, data.imag)
        elif isinstance(data, numbers.Number):
            return self.__format % data
        return str(data)

    def setData(self, data):
        if silx.io.is_dataset(data):
            data = data[()]
        text = self.toString(data)
        self.getWidget().setText(text)

    def getDataPriority(self, data):
        if data is None:
            return -1
        return 0


class DataViewer(qt.QFrame):
    """Widget to display any kind of data

    .. image:: img/DataViewer.png

    The method :meth:`setData` allows to set any data to the widget. Mostly
    `numpy.array` and `h5py.Dataset` are supported with adapted views. Other
    data types are displayed using a text viewer.

    A default view is automatically selected when a data is set. The method
    :meth:`setDisplayMode` allows to change the view. To have a graphical tool
    to select the view, prefer using the widget :class:`DataViewerFrame`.

    The dimension of the input data and the expected dimension of the selected
    view can differ. For example you can display an image (2D) from 4D
    data. In this case a :class:`NumpyAxesSelector` is displayed to allow the
    user to select the axis mapping and the slicing of other axes.

    .. code-block:: python

        import numpy
        data = numpy.random.rand(500,500)
        viewer = DataViewer()
        viewer.setData(data)
        viewer.setVisible(True)
    """

    EMPTY_MODE = 0
    PLOT1D_MODE = 1
    PLOT2D_MODE = 2
    TEXT_MODE = 3
    ARRAY_MODE = 4

    displayModeChanged = qt.Signal(int)
    """Emitted when the display mode changes"""

    dataChanged = qt.Signal()
    """Emitted when the data changes"""

    currentAvailableViewsChanged = qt.Signal()
    """Emitted when the current available views (which support the current
    data) change"""

    def __init__(self, parent=None):
        """Constructor

        :param QWidget parent: The parent of the widget
        """
        super(DataViewer, self).__init__(parent)

        self.__stack = qt.QStackedWidget(self)
        self.__numpySelection = NumpyAxesSelector(self)
        self.__numpySelection.selectedAxisChanged.connect(self.__numpyAxisChanged)
        self.__numpySelection.selectionChanged.connect(self.__numpySelectionChanged)

        self.setLayout(qt.QVBoxLayout(self))
        self.layout().addWidget(self.__stack, 1)

        group = qt.QGroupBox(self)
        group.setLayout(qt.QVBoxLayout())
        group.layout().addWidget(self.__numpySelection)
        group.setTitle("Axis selection")
        self.__axisSelection = group

        self.layout().addWidget(self.__axisSelection)

        self.__currentAvailableViews = []
        self.__currentView = None
        self.__data = None
        self.__useAxisSelection = False

        views = [
            _EmptyView(self.__stack, self.EMPTY_MODE),
            _Plot1dView(self.__stack, self.PLOT1D_MODE),
            _Plot2dView(self.__stack, self.PLOT2D_MODE),
            _TextView(self.__stack, self.TEXT_MODE),
            _ArrayView(self.__stack, self.ARRAY_MODE),
        ]
        self.__views = {}
        for v in views:
            self.__views[v.modeId()] = v

        # store stack index for each views
        self.__index = {}

        self.setDisplayMode(self.EMPTY_MODE)

    def clear(self):
        """Clear the widget"""
        self.setData(None)

    def __getStackIndex(self, view):
        """Get the stack index containing the view.

        :param DataView view: The view
        """
        if view not in self.__index:
            widget = view.getWidget()
            index = self.__stack.addWidget(widget)
            self.__index[view] = index
        else:
            index = self.__index[view]
        return index

    def __clearCurrentView(self):
        """Clear the current selected view"""
        view = self.__currentView
        if view is not None:
            view.clear()

    def __updateNumpySelectionAxis(self):
        """
        Update the numpy-selector according to the needed axis names
        """
        previous = self.__numpySelection.blockSignals(True)
        self.__numpySelection.clear()
        axisNames = self.__currentView.axiesNames()
        if len(axisNames) > 0:
            self.__useAxisSelection = True
            self.__axisSelection.setVisible(True)
            self.__numpySelection.setAxisNames(axisNames)
            self.__numpySelection.setData(self.__data)
        else:
            self.__useAxisSelection = False
            self.__axisSelection.setVisible(False)
        self.__numpySelection.blockSignals(previous)

    def __updateDataInView(self):
        """
        Update the views using the current data
        """
        if self.__useAxisSelection:
            data = self.__numpySelection.selectedData()
        else:
            data = self.__data

        self.__currentView.setData(data)

    def __setDisplayedView(self, view):
        """Set the displayed view.

        Change the displayed view according to the view itself.

        :param DataView view: The DataView to use to display the data
        """
        if self.__currentView is view:
            return
        self.__clearCurrentView()
        self.__currentView = view
        self.__updateNumpySelectionAxis()
        self.__updateDataInView()
        stackIndex = self.__getStackIndex(self.__currentView)
        self.__stack.setCurrentIndex(stackIndex)
        self.displayModeChanged.emit(view.modeId())

    def setDisplayMode(self, modeId):
        """Set the displayed view using display mode.

        Change the displayed view according to the requested mode.

        :param int modeId: Display mode, one of

            - `EMPTY_MODE`: display nothing
            - `PLOT1D_MODE`: display the data as a curve
            - `PLOT2D_MODE`: display the data as an image
            - `TEXT_MODE`: display the data as a text
            - `ARRAY_MODE`: display the data as a table
        """
        try:
            view = self.__views[modeId]
        except KeyError:
            raise ValueError("Display mode %s is unknown" % modeId)
        self.__setDisplayedView(view)

    def __updateView(self):
        """Display the data using the widget which fit the best"""
        data = self.__data

        # sort available views according to priority
        priorities = [v.getDataPriority(data) for v in self.__views.values()]
        views = zip(priorities, self.__views.values())
        views = filter(lambda t: t[0] >= 0, views)
        views = sorted(views, reverse=True)

        # store available views
        if len(views) == 0:
            self.__setCurrentAvailableViews([])
        else:
            if views[0][0] != 0:
                # remove 0-priority, if other are available
                views = list(filter(lambda t: t[0] != 0, views))
            available = [v[1] for v in views]
            self.__setCurrentAvailableViews(available)

        # display the view with the most priority (the default view)
        if len(views) > 0:
            view = views[0][1]
        else:
            view = self.__views[DataViewer.EMPTY_MODE]
        self.__clearCurrentView()
        self.__setDisplayedView(view)

    def __setCurrentAvailableViews(self, availableViews):
        """Set the current available viewa

        :param List[DataView] availableViews: Current available viewa
        """
        self.__currentAvailableViews = availableViews
        self.currentAvailableViewsChanged.emit()

    def currentAvailableViews(self):
        """Returns the list of available views for the current data

        :rtype: List[DataView]
        """
        return self.__currentAvailableViews

    def availableViews(self):
        """Returns the list of registered views

        :rtype: List[DataView]
        """
        return self.__views.values()

    def setData(self, data):
        """Set the data to view.

        It mostly can be a h5py.Dataset or a numpy.ndarray. Other kind of
        objects will be displayed as text rendering.

        :param numpy.ndarray data: The data.
        """
        self.__data = data
        self.__updateView()
        self.__updateNumpySelectionAxis()
        self.__updateDataInView()
        self.dataChanged.emit()

    def __numpyAxisChanged(self):
        """
        Called when axis selection of the numpy-selector changed
        """
        self.__clearCurrentView()

    def __numpySelectionChanged(self):
        """
        Called when data selection of the numpy-selector changed
        """
        self.__updateDataInView()

    def data(self):
        """Returns the data"""
        return self.__data

    def displayMode(self):
        """Returns the current display mode"""
        return self.__currentView.modeId()