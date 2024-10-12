import neurotorch.gui.window as window

class API():
    def GUI():
        """
            The GUI object is holding all objects when running Neurotorch GUI including the loaded Image, the extracted data and the
            gui objects.
        """
        return window.GUI

    def GUI_IMGObj():
        """
            The open image is stored into this wrapper class next to the calculated image data, for example the diffImage or the image
            stats (min, max, median, ...)
        """
        return window.GUI.IMG
    
    def GUI_Img():
        """
            The currently loaded Image (or None if no image loaded) as an np.ndarray of shape (t, y, x)
        """
        return window.GUI.IMG.img
    
    def GUI_ImgDiff():
        """
            The calculated diffImage from the currently loaded Image as an np.ndarray of shape (t, y, x)
        """
        return window.GUI.IMG.imgDiff
    
    def TabROI_DetectionResult():
        return window.GUI.tab3.detectionResult
