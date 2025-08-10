import tkinter as tk
from tkinter import ttk
from typing import Callable, Type, Literal
import re
import pandas as pd

from ..window import *

from ...utils.synapse_detection import *

class SynapseTreeview(ttk.Treeview):
    """
        A treeview component to display Synapses. Provides GUI components to edit them.
    """

    # Constant to export data as Stream
    TO_STREAM = "TO_STREAM"
    API_rightClickHooks = []

    editableFiels = [
        "CircularSynapseROI.Frame",
        "CircularSynapseROI.Center",
        "CircularSynapseROI.Radius",
    ]

    def __init__(self, 
                 master, 
                 session: Session, 
                 detection_result: DetectionResult,
                 selectCallback: Callable[[ISynapse|None, ISynapseROI|None], None], 
                 updateCallback = Callable[[None], None], 
                 allowSingleframe: bool = False,
                 allowMultiframe: bool = False,
                 **kwargs):
        """
            Parameters:
                    synapseCallback: Callable to return the current list of Synapses. Used to emulate a by ref behaviour
                    selectCallback: Called when the user selects a specific ISynapse. Called with None, if the user deselects from any ISynapse
                    updateCallback: Called when a property of a synapse is changed
        """
        self.master = master
        self.option_allowAddingSingleframeSynapses = allowSingleframe
        self.option_allowAddingMultiframeSynapses = allowMultiframe
        self.frame = ttk.Frame(self.master)
        self.frametv = ttk.Frame(self.frame)
        self.frametv.pack(fill="both")

        super().__init__(master=self.frametv, columns=("Val"), **kwargs)
        self.heading("#0", text="Property")
        self.heading("#1", text="Value")
        self.column("#0", minwidth=0, width=100, stretch=False)
        self.column("#1", minwidth=0, width=150, stretch=False)
        self.tag_configure("staged_synapse", foreground="#9416a6")

        self.scrollbar = ttk.Scrollbar(self.frametv, orient="vertical", command=self.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill="y")
        super().pack(fill="both", padx=10)
        self.scrollbarx = ttk.Scrollbar(self.frametv, orient="horizontal", command=self.xview)
        self.scrollbarx.pack(side=tk.BOTTOM, fill="x")

        self.frameButtons = tk.Frame(self.frame)
        self.frameButtons.pack()
        _btn_padx = 5
        if self.option_allowAddingSingleframeSynapses:
            self.btnAdd = tk.Button(self.frameButtons, text="+ Add", command = lambda: self._OnContextMenu_Add("Singleframe_CircularROI"))
            self.btnAdd.pack(side=tk.LEFT, padx=_btn_padx)
        if self.option_allowAddingMultiframeSynapses:
            self.btnAdd_Multiframe = tk.Button(self.frameButtons, text="+ Add Synapse", command= lambda: self._OnContextMenu_Add("MultiframeSynapse"))
            self.btnAdd_Multiframe.pack(side=tk.LEFT, padx=_btn_padx)

        self.btnRemove = tk.Button(self.frameButtons, text="🗑 Remove", state="disabled", command=self._BtnRemoveClick)
        self.btnRemove.pack(side=tk.LEFT, padx=_btn_padx)
        self.btnStage = tk.Button(self.frameButtons, text="🔒 Stage", state="disabled", command=self._BtnStageClick)
        self.btnStage.pack(side=tk.LEFT, padx=_btn_padx)

        tk.Label(self.frame, text="Use Right-Click to edit").pack(fill="x")
        tk.Label(self.frame, text="Double click on values to modify them").pack(fill="x")

        self.configure(yscrollcommand = self.scrollbar.set)
        self.configure(xscrollcommand = self.scrollbarx.set)
        self.bind("<<TreeviewSelect>>", self._OnSelect)
        self.bind("<Double-1>", self._OnDoubleClick)
        self.bind("<Button-3>", self._OnRightClick)

        self.modified = False
        self.detection_result = detection_result # Returns dict of UUID -> ISynapse
        self._selectCallback = selectCallback
        self._updateCallback = updateCallback

        self.session = session
        self._entryPopup = None
        self._sync_task = Task(function=self._SyncSynapses_task, name="syncing synapse treeview", run_async=True, keep_alive=True)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def SyncSynapses(self):
        """ Display the given list of ISynapse in the treeview. Updates existing values to keep the scrolling position. """
        self._sync_task.start()

    def _SyncSynapses_task(self, task:Task):
        task.set_indeterminate()
        try: 
            if self._entryPopup is not None:
                self._entryPopup.destroy()
        except AttributeError:
            pass    
        synapses = self.detection_result.synapses_dict
        synapses = dict(sorted(synapses.items(), key=lambda item: (not item[1].staged, item[1].location[0] , item[1].location[1]) if item[1].location is not None else (not item[1].staged, 0, 0)))
        #self._synapseCallback(synapses)

        for _uuid in ((uuidsOld := set(self.get_children(''))) - (uuidsNew := set(synapses.keys()))):
            self.delete(_uuid) # Delete removed entries
        for _uuid in (uuidsNew - uuidsOld):
            isSingleframe = isinstance(synapses[_uuid], SingleframeSynapse)
            self.insert('', 'end', iid=_uuid, text='', open=(not isSingleframe)) # Create template node for newly added entries
        synapse_index = 1 # Index to label synapses without a name
        for i, (_uuid, s) in enumerate(synapses.items()):
            if self.index(_uuid) != i: # Keep the order the same as in the list
                self.move(_uuid, '', i)
            name = s.name
            if name is None:
                name = f"Synapse {synapse_index}"
                synapse_index += 1
            isSingleframe = isinstance(s, SingleframeSynapse)
            self.item(_uuid, text=name)
            self.item(_uuid, values=[s.get_roi_description()])
            self.item(_uuid, tags=(("staged_synapse",) if s.staged else ()))

            # Now the same procedure for the ISynapseROIs
            rois = dict(sorted(s.rois_dict.items(), key=lambda item: item[1].frame if item[1].frame is not None else -1))
            for _ruuid in ((uuidsOld := set(self.get_children(_uuid))) - (uuidsNew := set(rois.keys()))):
                self.delete(_ruuid)
            for _ruuid in (uuidsNew - uuidsOld):
                self.insert(_uuid, 'end', iid=_ruuid, text='', open=isSingleframe)

            for si, (_ruuid, r) in enumerate(rois.items()):
                if self.index(_ruuid) != si:
                    self.move(_ruuid, _uuid, si)
                self._UpdateISynapseROI(r)
        if len(self.get_children('')) == 0:
            self.btnRemove.config(state="disabled")
            self.btnStage.config(state="disabled")

    def GetSynapseByRowID(self, rowid: str) -> tuple[ISynapse|None, ISynapseROI|None]:
        """ 
            Given a rowid, return the corrosponding ISynapse and ISynapseROI as tuple (ISynapse, ISynapseROI).
            If provided with a ISynapse row, return (ISynapse, None). If provided with a root node, return (None, None).
        """
        if rowid is None: return (None, None)
        parents = [rowid]
        while parents[-1] != '':
            parents.append(self.parent(parents[-1]))
        if len(parents) < 2:
            return (None, None)
        synapse_uuid = parents[-2]
        if synapse_uuid not in self.detection_result.synapses_dict.keys():
            logger.warning(f"SynapseTreeview: Can't find synapse {synapse_uuid} in the callback")
            return (None, None)
        synapse = self.detection_result.synapses_dict[synapse_uuid]
        if len(parents) < 3:
            return (synapse, None)
        roi_uuid = parents[-3]
        if roi_uuid not in synapse.rois_dict.keys():
            logger.warning(f"SynapseTreeview: Can't find ROI {roi_uuid} in synapse {synapse_uuid}")
            return (synapse, None)
        roi = synapse.rois_dict[roi_uuid]
        return (synapse, roi)
    
    def GetSelectedSynapse(self) -> tuple[ISynapse|None, ISynapseROI|None]:
        """
            Identifies the currently selected rowid and returns the result of GetSynapseByRowID
        """
        selection = self.selection()
        if len(selection) != 1:
            return (None, None)
        rowid = selection[0]
        synapse, roi = self.GetSynapseByRowID(rowid)
        return synapse, roi
    
    def Select(self, synapse: ISynapse|None = None, roi:ISynapseROI|None = None):
        """
            Selects an entry based on synapse or roi ID and scrolls to it. As a convenience feature, if both synapse and ROI are given,
            it will select the synapse if the node is collapsed and the ROI in the other case.
        """
        if synapse is None and roi is None:
            raise ValueError("Selecting a row in a synapse entry requires at least a synapse or ROI uuid")
        if synapse is not None and not isinstance(synapse, ISynapse):
            raise ValueError(f"The provided synapse is of type {type(synapse)}")
        if roi is not None and not isinstance(roi, ISynapseROI):
            raise ValueError(f"The provided ROI is of type {type(roi)}")
        if roi is not None and (synapse is None or self.item(synapse.uuid, "open") or len(synapse.rois) >= 2):
            self.selection_set(roi.uuid)
            self.see(roi.uuid)
        elif synapse is not None:
            self.selection_set(synapse.uuid)
            self.see(synapse.uuid)
        
    def _OnSelect(self, event):
        """ Triggered on selecting a row in the Treeview. Determines the corrosponding ISynapse and passes it back to the callback. """
        selection = self.selection()
        if len(selection) != 1:
            self._selectCallback(None, None)
            return
        rowid = selection[0]
        synapse, roi = self.GetSynapseByRowID(rowid)
        if synapse is not None or roi is not None:
            self.btnRemove.config(state="active")
            self.btnStage.config(state="active")
        else:
            self.btnRemove.config(state="disabled")
            self.btnStage.config(state="disabled")
        self._selectCallback(synapse, roi)

    def _OnDoubleClick(self, event):
        """ Triggered on double clicking and creates a editable field if the clicked field is editable """
        try: 
            if self._entryPopup is not None:
                self._entryPopup.destroy()
        except AttributeError:
            pass    
        rowid = self.identify_row(event.y)
        column = self.identify_column(event.x)
        if rowid is None: return
        rowid_fiels = rowid.split("_")
        synapse, roi = self.GetSynapseByRowID(rowid)

        if column == "#0": # Catches editable Synapse Name
            if synapse is None or roi is not None: 
                return
        elif column == "#1": # Catches editable fields
            if len(rowid_fiels) < 2: return # Editable rows have form {roi.uuid}_{modifiable_field_name}
            if rowid_fiels[1] not in SynapseTreeview.editableFiels: return
            if synapse is None or roi is None: return
        else:
            return
        

        self._entryPopup = EntryPopup(self, self._OnEntryChanged, rowid, column)
        self._entryPopup.place_auto()
        return "break"

    def _OnRightClick(self, event):
        """ Triggered on right clicking in the Treeview. Opens a context menu. """
        rowid = self.identify_row(event.y)
        synapse, roi = self.GetSynapseByRowID(rowid)

        contextMenu = tk.Menu(self.master, tearoff=0)
        addMenu = tk.Menu(contextMenu, tearoff=0)
        if self.option_allowAddingSingleframeSynapses or self.option_allowAddingMultiframeSynapses:
            if self.option_allowAddingSingleframeSynapses:
                addMenu.add_command(label="Circular ROI Synapse", command = lambda: self._OnContextMenu_Add("Singleframe_CircularROI"))
            if self.option_allowAddingMultiframeSynapses:
                addMenu.add_command(label="Multiframe Synapse", command = lambda: self._OnContextMenu_Add("MultiframeSynapse"))  
            contextMenu.add_cascade(menu=addMenu, label="Add")

        stageMenu = tk.Menu(contextMenu, tearoff=0)
        stageMenu.add_command(label="All to stage", command = self._OnContextMenu_AllToStage)    
        stageMenu.add_command(label="All from stage", command = self._OnContextMenu_AllFromStage)  
        contextMenu.add_cascade(menu=stageMenu, label="Stage")  

        clearMenu = tk.Menu(contextMenu, tearoff=0)
        clearMenu.add_command(label="Clear", command= lambda: self.ClearSynapses('non_staged'))
        clearMenu.add_command(label="Clear staged", command= lambda: self.ClearSynapses('staged'))
        clearMenu.add_command(label="Clear all", command= lambda: self.ClearSynapses('all'))
        contextMenu.add_cascade(menu=clearMenu, label="Clear/Remove")

        importMenu = tk.Menu(contextMenu, tearoff=0)
        importMenu.add_command(label="Import from ImageJ", command=self.ImportROIsImageJ)
        contextMenu.add_cascade(menu=importMenu, label="Import")

        exportMenu = tk.Menu(contextMenu, tearoff=0)
        exportMenu.add_command(label="Export to ImageJ", command=self.ExportROIsImageJ)
        exportMenu.add_command(label="Export as file", command=self.ExportCSVMultiM)
        contextMenu.add_cascade(menu=exportMenu, label="Export")

        for f in SynapseTreeview.API_rightClickHooks:
            try:
                f(contextMenu, importMenu, exportMenu)
            except Exception as ex:
                logger.error(f"SynapseTreeview: Failed to execute hook {str(f)} with the following error: {ex}")

        if synapse is not None or roi is not None:
            clearMenu.insert_separator(index=0)
            stageMenu.insert_separator(index=0)

        if synapse is not None:
            if synapse.name is not None:
                clearMenu.insert_command(index=0, label="Reset name", command = lambda: self._OnContextMenu_ResetName(synapse=synapse))
            clearMenu.insert_command(index=0, label="Remove Synapse", command = lambda: self._OnContextMenu_Remove(synapse=synapse))
            stageMenu.insert_command(index=0, label="Toggle Stage", command = lambda: self._OnContextMenu_ToggleStage(synapse=synapse))

            if isinstance(synapse, MultiframeSynapse):
                addMenu.add_separator()
                addMenu.add_command(label="Circular ROI",  command = lambda: self._OnContextMenu_Add("CircularROI", synapse=synapse))

        if roi is not None and isinstance(synapse, MultiframeSynapse):
            clearMenu.insert_command(index=0, label="Remove ROI", command = lambda: self._OnContextMenu_Remove(synapse=synapse, roi=roi))

        contextMenu.post(event.x_root, event.y_root)  
        

    def _OnEntryChanged(self, rowid, column, oldval: str, val: str):
        """ Called after a EntryPopup closes with a changed value. Determines the corresponding ISynapse and modifies it"""

        rowid_fiels = rowid.split("_")
        synapse, roi = self.GetSynapseByRowID(rowid)

        if column == "#0": # Catches editable Synapse Name
            if synapse is None or roi is not None: 
                return
            synapse.name = val
            logger.debug(f"Renamed synapse {synapse.uuid} to '{val}'")
        elif column == "#1": # Catches editable fields
            if len(rowid_fiels) < 2: return # Editable rows have form {roi.uuid}_{modifiable_field_name}
            if rowid_fiels[1] not in SynapseTreeview.editableFiels: return
            if synapse is None or roi is None: return

            match (rowid_fiels[1]):
                case "CircularSynapseROI.Frame":
                    if not val.isdigit() or int(val) < 1:
                        logger.debug(f"Invalid input for edtiable field '{rowid_fiels[1]}': {val}")
                        self.master.bell()
                        return
                    roi.set_frame(int(val) - 1)
                    logger.debug(f"Modified frame of CircularSynapseROI to {roi.frame}")
                case "CircularSynapseROI.Center":
                    if (_match := re.match(r"^(\d+),(\d+)$", val.replace(" ", "").replace("(", "").replace(")", ""))) is None or len(_match.groups()) != 2:
                        logger.debug(f"Invalid input for edtiable field '{rowid_fiels[1]}': {val}")
                        self.master.bell()
                        return
                    roi.set_location(int(x=_match.groups()[0]), y=int(_match.groups()[1]))
                    logger.debug(f"Modified location of CircularSynapseROI to {roi.LocationStr}")
                case "CircularSynapseROI.Radius":
                    if not val.isdigit():
                        logger.debug(f"Invalid input for edtiable field '{rowid_fiels[1]}': {val}")
                        self.master.bell()
                        return
                    roi.set_radius(int(val))
                    logger.debug(f"Modified location of CircularSynapseROI to {roi.radius}")
                case _:
                    logger.warning(f"SynapseTreeview: Unexpected invalid editable field {rowid_fiels[1]}")
                    return
        else:
            return
        
        self.modified = True
        self.SyncSynapses()
        self._updateCallback()
        

    def _UpdateISynapseROI(self, roi: ISynapseROI):
        """ Updates the values in the treeview for a given ISynapseROI """
        _ruuid = roi.uuid
        self.delete(*self.get_children(_ruuid))
        if roi.frame is not None:
            self.insert(_ruuid, 'end', iid=f"{_ruuid}_CircularSynapseROI.Frame", text="Frame", values=[roi.frame + 1])

        if roi.signal_strength is not None:
            self.insert(_ruuid, 'end', iid=f"{_ruuid}_CircularSynapseROI.SignalStrength", text="Signal Strength", values=[roi.signal_strength])
        
        if type(roi) == CircularSynapseROI:
            type_ = "Circular ROI"
            self.insert(_ruuid, 'end', iid=f"{_ruuid}_CircularSynapseROI.Radius", text="Radius", values=[roi.radius if roi.radius is not None else ''])
            self.insert(_ruuid, 'end', iid=f"{_ruuid}_CircularSynapseROI.Center", text="Center(X,Y)",  values=[roi.location_string])
        elif type(roi) == PolygonalSynapseROI:
            type_ = "Polygonal ROI"
        else:
            type_ = "Undefined ROI"

        if roi.region_props is not None:
            rp = roi.region_props
            rp_id = f"{_ruuid}_RegionProperties"
            self.insert(_ruuid, 'end', iid=f"{_ruuid}_RegionProperties", text="Properties", values=[])
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.Area", text="Area [px]", values=[rp.area])
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.CircleRadius", text=f"Radius of circle with same size [px]", values=([f"{round(rp.equivalent_diameter_area/2, 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.Eccentricity", text=f"Eccentricity [0,1)", values=([f"{round(rp.eccentricity, 3)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.SignalMax", text=f"Signal Maximum", values=([f"{round(rp.intensity_max, 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.SignalMin", text=f"Signal Minimum", values=([f"{round(rp.intensity_min, 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.SignalMean", text=f"Signal Mean", values=([f"{round(rp.intensity_mean, 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.SignalStd", text=f"Signal Std.", values=([f"{round(rp.intensity_std, 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.InertiaX", text=f"Inertia X", values=([f"{round(rp.inertia_tensor[0,0], 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.InertiaY", text=f"Inertia Y", values=([f"{round(rp.inertia_tensor[1,1], 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.InertiaRatio", text=f"Inertia Ratio", values=([f"{round(rp.inertia_tensor[0,0]/rp.inertia_tensor[1,1], 2)}"]))
        self.item(_ruuid, text=type_, values=[f"Frame {roi.frame + 1}" if roi.frame is not None else ''])

    # Button Clicks

    def _BtnRemoveClick(self):
        """ Triggered when clicking the Remove button """
        synapse, roi = self.GetSelectedSynapse()
        if synapse is not None and roi is not None and self.option_allowAddingMultiframeSynapses:
            self._OnContextMenu_Remove(synapse, roi)
        elif synapse is not None:
            self._OnContextMenu_Remove(synapse)
        else:
            self.master.bell()
            
    def _BtnStageClick(self):
        """ Triggered when clicking the Stage button """
        synapse, roi = self.GetSelectedSynapse()
        if synapse is not None:
            self._OnContextMenu_ToggleStage(synapse)
        else:
            self.master.bell()

    # Context Menu Clicks

    def _OnContextMenu_Add(self, class_: Literal["CircularROI", "PolyonalROI", "MultiframeSynapse", "Singleframe_CircularROI", "Singleframe_PolyonalROI"], synapse: ISynapse|None = None):
        if isinstance(synapse, MultiframeSynapse):
            match class_:
                case "CircularROI":
                    r = CircularSynapseROI().set_radius(6).set_location(x=0,y=0).set_frame(0)
                case "PolyonalROI":
                    r = PolygonalSynapseROI().set_frame(0)
                case _:
                    return
            s = cast(MultiframeSynapse, self.detection_result.synapses_dict[synapse.uuid])
            s.add_roi(r)
        else:
            match class_:
                case "Singleframe_CircularROI":
                    s = SingleframeSynapse(CircularSynapseROI().set_radius(6).set_location(x=0,y=0))
                case "Singleframe_PolyonalROI":
                    s = SingleframeSynapse(PolygonalSynapseROI())
                case "MultiframeSynapse":
                    s = MultiframeSynapse()
                case _:
                    return
            self.detection_result.synapses_dict[s.uuid] = s
        self.modified = True
        self.SyncSynapses()
        self._updateCallback()

    def _OnContextMenu_AllToStage(self):
        for s in self.detection_result.synapses_dict.values():
            s.staged = True
        self.SyncSynapses()

    def _OnContextMenu_AllFromStage(self):
        for s in self.detection_result.synapses_dict.values():
            s.staged = False
        self.SyncSynapses()

    def _OnContextMenu_ToggleStage(self, synapse: ISynapse):
        synapse.staged = not synapse.staged
        self.SyncSynapses()
    
    def _OnContextMenu_Remove(self, synapse: ISynapse = None, roi: ISynapseROI = None):
        if synapse is not None and roi is not None:
            if roi.uuid not in synapse.rois_dict.keys():
                logger.warning(f"SynapseTreeview: Can't remove ROI {synapse.uuid} from synapse {synapse.uuid} as it isn't contained")
                return
            del synapse.rois_dict[roi.uuid]
        elif synapse is not None:
            if synapse.uuid not in self.detection_result.synapses_dict.keys():
                logger.warning(f"SynapseTreeview: Can't remove synapse {synapse.uuid} as it does not exist")
                return
            self.detection_result.synapses_dict.pop(synapse.uuid)
        self.modified = True
        self.SyncSynapses()
        self._updateCallback()

    def _OnContextMenu_ResetName(self, synapse: ISynapse):
        synapse.name = None
        self.SyncSynapses()
        self._updateCallback()

    def ImportROIsImageJ(self):
        if self.session.ijH is None or self.session.ijH.ij is None:
            messagebox.showerror("Neurotorch", "You must first start Fiji/ImageJ")
            return
        res = self.session.ijH.import_rois()
        if res is None:
            self.root.bell()
            return
        rois, names = res[0], res[1]
        if len(rois) == 0:
            self.root.bell()
            return
        synapses = self.detection_result.synapses_dict
        for i in range(len(rois)):
            s = SingleframeSynapse(rois[i]).set_name(names[i])
            synapses[s.uuid] = s
        self.SyncSynapses()
        self._updateCallback()

    def ExportROIsImageJ(self):
        if self.session.ijH is None or self.session.ijH.ij is None:
            messagebox.showerror("Neurotorch", "You must first start Fiji/ImageJ")
            return
        self.session.ijH.export_ROIS(list(self.detection_result.synapses_dict.values()))

    def ExportCSVMultiM(self, path:str|None = None, dropFrame=False) -> bool|None:
        synapses = self.detection_result.synapses_dict
        if len(synapses) == 0 or self.session.active_image_object is None or self.session.active_image_object.img is None:
            self.master.bell()
            return None
        data = pd.DataFrame()
        i_synapse = 1
        for synapse in synapses.values():
            name = synapse.name
            if synapse.name is None:
                name = f"Synapse {i_synapse}"
                i_synapse += 1
            for i, roi in enumerate(synapse.rois):
                name2 = name
                if len(synapse.rois) >= 2:
                    name2 += f" ROI {i} "
                name2 += "(" + roi.location_string.replace(",","|").replace(" ","") + ")"
                if name2 in list(data.columns.values):
                    for i in range(2, 10):
                        if f"{name2} ({i})" not in list(data.columns.values):
                            name2 = f"{name2} ({i})"
                            break
                signal = roi.get_signal_from_image(self.session.active_image_object.img)
                if signal.shape[0] == 0:
                    continue
                data[name2] = np.mean(signal, axis=1)
        data = data.round(4)
        data.index += 1

        if path == SynapseTreeview.TO_STREAM:
            return data.to_csv(lineterminator="\n",index=(not dropFrame))
        if path is None:
            path = filedialog.asksaveasfilename(title="Save Multi Measure", filetypes=(("CSV", "*.csv"), ("All files", "*.*")), defaultextension=".csv")
        if path is None or path == "":
            return None
        data.to_csv(path_or_buf=path, lineterminator="\n", mode="w", index=(not dropFrame))
        return True

    def ClearSynapses(self, target: Literal['staged', 'non_staged', 'all']):
        match(target):
            case 'staged':
                self.detection_result.synapses_dict = {_uuid: s for _uuid, s in self.detection_result.synapses_dict.items() if not s.staged}
            case 'non_staged':
                self.detection_result.synapses_dict = {_uuid: s for _uuid, s in self.detection_result.synapses_dict.items() if s.staged}
            case 'all':
                self.detection_result.clear()
            case _:
                return
        self.modified = False
        self.SyncSynapses()
        self._updateCallback()



class EntryPopup(ttk.Entry):
    """
        Implements editabled ttk Treeview entries
    """

    def __init__(self, tv: ttk.Treeview, callback, rowid, column, **kw):
        ttk.Style().configure('pad.TEntry', padding='1 1 1 1')
        super().__init__(tv, style='pad.TEntry', **kw)
        self.tv = tv
        self.callback = callback
        self.rowid = rowid
        self.column = column
        if self.column == "#0":
            self.oldval = self.tv.item(self.rowid, 'text')
        else:
            self.oldval = self.tv.item(self.rowid, 'values')[int(self.column[1:]) - 1]

        self.insert(0, self.oldval) 

        self.focus_force()
        self.select_all()
        self.bind("<Return>", self.on_return)
        self.bind("<Escape>", lambda *val1: self.destroy())
        self.bind("<FocusOut>", lambda *val1: self.destroy())

    def place_auto(self):
        bbox = self.tv.bbox(self.rowid, self.column)
        if bbox == "":
            return
        x,y,width,height = bbox
        pady = height // 2
        self.place(x=x, y=y+pady, width=width, height=height, anchor=tk.W)


    def on_return(self, event):
        val = self.get()
        try:
            if self.oldval != val:
                self.callback(self.rowid, self.column, self.oldval, val)
        finally:
            self.destroy()


    def select_all(self, *val1):
        self.selection_range(0, 'end')
        return 'break'