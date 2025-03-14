

class Session:
    """ A session is the main entry into Neurotorch. It stores the loaded data and provides update functions for the GUI """

    def __init__(self, headless: bool = False):
        """
            A session is the main entry into Neurotorch. It stores the loaded data and provides update functions for the GUI

            :param bool headless: If set to true, no GUI is launched. This allows to use the API without launching a GUI
        """
        
class SessionStorage:
    """ A session storage holds data for the current session and is for example passed between tabs in the GUI """

    SessionStorage

Session()