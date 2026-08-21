import ctypes
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt


@dataclass
class DefectRow:
    type_name: str
    sub_type: str
    index: int
    y_start: int
    y_end: int
    merged_start: int
    bound_rects: List[List[float]]
    details: Dict[str, Any]


class SickDataReaderGenerator:
    """Lightweight DLL-backed reader used by inspection UI."""

    class SickDataReader:
        def __init__(self, dll_handle, dat_home: str, scan_name: str):
            self._dll = dll_handle
            self._dat_handle = ctypes.c_void_p()
            self._is_valid = False
            self._init(dat_home, scan_name)

        def _init(self, dat_home: str, scan_name: str):
            msg_size = 1024
            msg = ctypes.create_string_buffer(msg_size)
            ok = self._dll.sick_dat_init(
                dat_home.encode("utf-8"),
                scan_name.encode("utf-8"),
                ctypes.byref(self._dat_handle),
                msg,
                ctypes.byref(ctypes.c_int(msg_size)),
                True,
            )
            self._is_valid = bool(ok)

        def is_valid(self) -> bool:
            return self._is_valid

        def get_dim(self):
            msg_size = 1024
            msg = ctypes.create_string_buffer(msg_size)
            lx = ctypes.c_int()
            ly = ctypes.c_int()
            rx = ctypes.c_int()
            ry = ctypes.c_int()
            w = ctypes.c_int()
            h = ctypes.c_int()
            ok = self._dll.sick_dat_get_dim(
                self._dat_handle,
                ctypes.byref(lx),
                ctypes.byref(ly),
                ctypes.byref(rx),
                ctypes.byref(ry),
                ctypes.byref(w),
                ctypes.byref(h),
                msg,
                ctypes.byref(ctypes.c_int(msg_size)),
            )
            if not ok:
                return None
            return lx.value, ly.value, rx.value, ry.value, w.value, h.value

        def get_combined_dim(self):
            msg_size = 1024
            msg = ctypes.create_string_buffer(msg_size)
            w = ctypes.c_int()
            h = ctypes.c_int()
            ok = self._dll.sick_dat_get_combined_dim(
                self._dat_handle,
                ctypes.byref(w),
                ctypes.byref(h),
                msg,
                ctypes.byref(ctypes.c_int(msg_size)),
            )
            if not ok:
                return None
            return w.value, h.value

        def get_resolution(self):
            msg_size = 1024
            msg = ctypes.create_string_buffer(msg_size)
            x_left = ctypes.c_float()
            y_left = ctypes.c_float()
            x_right = ctypes.c_float()
            y_right = ctypes.c_float()

            ok_left = self._dll.sick_dat_get_resolution(
                self._dat_handle,
                ctypes.c_bool(True),
                ctypes.byref(x_left),
                ctypes.byref(y_left),
                msg,
                ctypes.byref(ctypes.c_int(msg_size)),
            )
            ok_right = self._dll.sick_dat_get_resolution(
                self._dat_handle,
                ctypes.c_bool(False),
                ctypes.byref(x_right),
                ctypes.byref(y_right),
                msg,
                ctypes.byref(ctypes.c_int(msg_size)),
            )
            if not (ok_left and ok_right):
                return None
            return x_left.value, y_left.value, x_right.value, y_right.value

        def get_offset(self):
            msg_size = 1024
            msg = ctypes.create_string_buffer(msg_size)
            ox = ctypes.c_int()
            oy = ctypes.c_int()
            ok = self._dll.sick_dat_get_offset(
                self._dat_handle,
                ctypes.byref(ox),
                ctypes.byref(oy),
                msg,
                ctypes.byref(ctypes.c_int(msg_size)),
            )
            if not ok:
                return None
            return ox.value, oy.value

        def get_tag(self):
            msg_size = 1024
            msg = ctypes.create_string_buffer(msg_size)
            tag = self._dll.sick_dat_get_tag(
                self._dat_handle, msg, ctypes.byref(ctypes.c_int(msg_size))
            )
            if not tag:
                return ""
            return tag.decode("utf-8", errors="ignore")

        def get_version(self):
            msg_size = 1024
            msg = ctypes.create_string_buffer(msg_size)
            version = self._dll.get_version(self._dat_handle, msg, msg_size)
            if not version:
                return ""
            return version.decode("utf-8", errors="ignore")

        def get_has_reflectance(self):
            msg_size = 1024
            msg = ctypes.create_string_buffer(msg_size)
            return bool(
                self._dll.sick_dat_get_has_reflectance(
                    self._dat_handle, msg, ctypes.byref(ctypes.c_int(msg_size))
                )
            )

        def get_combined_relative_layer(
            self,
            start_x: int,
            start_y: int,
            width: int,
            height: int,
            use_alpha: bool = False,
        ):
            msg_size = 1024
            msg = ctypes.create_string_buffer(msg_size)
            if width <= 0 or height <= 0:
                return None

            vec_size = width * height
            img_vec = (ctypes.c_uint8 * vec_size)()
            img_ptr = ctypes.cast(img_vec, ctypes.POINTER(ctypes.c_uint8))
            ok = self._dll.sick_dat_get_combined_relative_layer(
                self._dat_handle,
                ctypes.byref(ctypes.c_int64(int(start_x))),
                ctypes.byref(ctypes.c_int64(int(start_y))),
                ctypes.byref(ctypes.c_int64(int(width))),
                ctypes.byref(ctypes.c_int64(int(height))),
                img_ptr,
                ctypes.byref(ctypes.c_uint64(vec_size)),
                msg,
                ctypes.byref(ctypes.c_int(msg_size)),
                ctypes.c_bool(use_alpha),
                ctypes.byref(ctypes.c_float(1.0)),
            )
            if not ok:
                return None
            return bytes(img_vec)

        def release(self):
            if not self._dat_handle:
                return
            msg_size = 1024
            msg = ctypes.create_string_buffer(msg_size)
            try:
                self._dll.sick_dat_release(
                    ctypes.byref(self._dat_handle),
                    msg,
                    ctypes.byref(ctypes.c_int(msg_size)),
                )
            except Exception:
                pass

        def __del__(self):
            self.release()

    def __init__(self, dll_path: str):
        self._dll = None
        self.dll_path = dll_path
        self.last_error = ""
        self.load_dll(dll_path)

    def load_dll(self, dll_path: str) -> bool:
        if not dll_path:
            self.last_error = "DLL path is empty."
            return False
        abs_dll = os.path.abspath(dll_path)
        if not os.path.isfile(abs_dll):
            self._dll = None
            self.last_error = f"DLL not found: {abs_dll}"
            return False

        try:
            dll_dir = os.path.dirname(abs_dll)
            add_dir = getattr(os, "add_dll_directory", None)
            if callable(add_dir):
                add_dir(dll_dir)
            dll = ctypes.windll.LoadLibrary(abs_dll)
        except Exception as exc:
            self._dll = None
            self.last_error = f"Failed to load DLL: {exc}"
            return False

        self._dll = dll
        self.dll_path = abs_dll

        if hasattr(dll, "sick_dat_get_tag"):
            dll.sick_dat_get_tag.restype = ctypes.c_char_p
        if hasattr(dll, "get_version"):
            dll.get_version.restype = ctypes.c_char_p
        if hasattr(dll, "sick_dat_get_has_reflectance"):
            dll.sick_dat_get_has_reflectance.restype = ctypes.c_bool
        self.last_error = ""
        return True

    def generate(self, dat_home: str, scan_name: str):
        if self._dll is None:
            return None
        reader = self.SickDataReader(self._dll, dat_home, scan_name)
        return reader if reader.is_valid() else None


class ManualInspectionDialog(QtWidgets.QDialog):
    jump_requested = QtCore.pyqtSignal(str, int, str)
    open_front_cam_requested = QtCore.pyqtSignal(str, int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Manual Inspection"))
        self.resize(1040, 720)

        self._detection_json_data: Dict = {}
        self._sub_type_keys: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._detection_length = 5000
        self._non_overlap_length = 4500
        self._scan_name = ""
        self._reader = None
        self._dat_reader = None
        self._rows: List[DefectRow] = []
        self._dat_home = ""
        self._scan_y_start = 0
        self._scan_height = 0
        self._combined_width = 0
        self._combined_height = 0
        self._res_x_left = 1.0
        self._res_y_left = 1.0
        self._source_json_path = ""
        self._runtime_preview_dialog = None
        self._runtime_preview_label = None
        self._runtime_preview_info_label = None
        self._runtime_last_pixmap = None
        self._detection_payload: Dict = {}

        self._setup_ui()
        self._suggest_default_paths()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QGridLayout()

        self.dll_path_edit = QtWidgets.QLineEdit("ipas_dat_reader_dll.dll")
        self.dat_home_edit = QtWidgets.QLineEdit(
            r"\\Synology_NAS_8\Scanning_DATA\file-service\dat_v4"
        )
        self.scan_name_combo = QtWidgets.QComboBox()
        self.scan_name_combo.setEditable(True)
        self.scan_name_combo.addItem("2026_01_14 15_56_54")
        self.det_version_combo = QtWidgets.QComboBox()
        self.det_version_combo.setEditable(True)
        self.det_version_combo.addItem("v1.0.0.0")
        self.local_json_dir_edit = QtWidgets.QLineEdit("C:\\")
        self.json_file_edit = QtWidgets.QLineEdit("")
        self.use_local_json_check = QtWidgets.QCheckBox(
            self.tr("Use Local global_<scan>.json")
        )
        self.use_json_file_check = QtWidgets.QCheckBox(
            self.tr("Use Specific JSON File")
        )

        browse_dll_btn = QtWidgets.QPushButton(self.tr("Browse"))
        browse_json_btn = QtWidgets.QPushButton(self.tr("Browse"))
        browse_json_file_btn = QtWidgets.QPushButton(self.tr("Browse"))
        refresh_scan_btn = QtWidgets.QPushButton(self.tr("Refresh"))
        refresh_version_btn = QtWidgets.QPushButton(self.tr("Refresh"))
        load_btn = QtWidgets.QPushButton(self.tr("Load"))

        form.addWidget(QtWidgets.QLabel(self.tr("DLL Path")), 0, 0)
        form.addWidget(self.dll_path_edit, 0, 1)
        form.addWidget(browse_dll_btn, 0, 2)

        form.addWidget(QtWidgets.QLabel(self.tr("DAT Home")), 1, 0)
        form.addWidget(self.dat_home_edit, 1, 1, 1, 2)

        form.addWidget(QtWidgets.QLabel(self.tr("Scan Name")), 2, 0)
        form.addWidget(self.scan_name_combo, 2, 1)
        form.addWidget(refresh_scan_btn, 2, 2)

        form.addWidget(QtWidgets.QLabel(self.tr("Detection Version")), 3, 0)
        form.addWidget(self.det_version_combo, 3, 1)
        form.addWidget(refresh_version_btn, 3, 2)

        form.addWidget(self.use_local_json_check, 4, 0, 1, 3)
        form.addWidget(self.use_json_file_check, 5, 0, 1, 3)
        form.addWidget(QtWidgets.QLabel(self.tr("Local Json Folder")), 6, 0)
        form.addWidget(self.local_json_dir_edit, 6, 1)
        form.addWidget(browse_json_btn, 6, 2)
        form.addWidget(QtWidgets.QLabel(self.tr("Json File")), 7, 0)
        form.addWidget(self.json_file_edit, 7, 1)
        form.addWidget(browse_json_file_btn, 7, 2)

        form.addWidget(load_btn, 8, 2)

        layout.addLayout(form)

        self.meta_label = QtWidgets.QLabel(self.tr("Ready"))
        self.meta_label.setWordWrap(True)
        layout.addWidget(self.meta_label)

        filter_layout = QtWidgets.QHBoxLayout()
        self.type_combo = QtWidgets.QComboBox()
        self.subtype_combo = QtWidgets.QComboBox()
        filter_layout.addWidget(QtWidgets.QLabel(self.tr("Type")))
        filter_layout.addWidget(self.type_combo, 1)
        filter_layout.addWidget(QtWidgets.QLabel(self.tr("Sub Type")))
        filter_layout.addWidget(self.subtype_combo, 1)
        layout.addLayout(filter_layout)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("Index"),
                self.tr("Y Start"),
                self.tr("Y End"),
                self.tr("Merged Start"),
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        layout.addWidget(self.table, 1)

        self.selection_info_label = QtWidgets.QLabel(
            self.tr("Selected Defect: none")
        )
        self.selection_info_label.setWordWrap(True)
        layout.addWidget(self.selection_info_label)

        button_layout = QtWidgets.QHBoxLayout()
        self.jump_btn = QtWidgets.QPushButton(self.tr("Open Runtime DAT View"))
        self.front_cam_btn = QtWidgets.QPushButton(self.tr("Open Matched Front-Cam"))
        self.log_cmd_btn = QtWidgets.QPushButton(
            self.tr("OfflineTest_Exe_Log_Cmd")
        )
        self.log_all_cmd_btn = QtWidgets.QPushButton(
            self.tr("All_Sub_Type_Log_Cmd")
        )
        self.save_as_btn = QtWidgets.QPushButton(self.tr("Save As Json"))
        button_layout.addWidget(self.jump_btn)
        button_layout.addWidget(self.front_cam_btn)
        button_layout.addWidget(self.log_cmd_btn)
        button_layout.addWidget(self.log_all_cmd_btn)
        button_layout.addWidget(self.save_as_btn)
        layout.addLayout(button_layout)

        browse_dll_btn.clicked.connect(self._browse_dll)
        browse_json_btn.clicked.connect(self._browse_local_json_dir)
        browse_json_file_btn.clicked.connect(self._browse_json_file)
        refresh_scan_btn.clicked.connect(self._refresh_scan_name_options)
        refresh_version_btn.clicked.connect(
            self._refresh_detection_version_options
        )
        load_btn.clicked.connect(self._load_session)
        self.dat_home_edit.editingFinished.connect(
            self._refresh_scan_name_options
        )
        self.dat_home_edit.editingFinished.connect(
            self._refresh_detection_version_options
        )
        self.scan_name_combo.currentTextChanged.connect(
            lambda _value: self._refresh_detection_version_options()
        )
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.subtype_combo.currentTextChanged.connect(self._populate_rows)
        self.jump_btn.clicked.connect(self._emit_jump)
        self.front_cam_btn.clicked.connect(self._emit_front_cam)
        self.log_cmd_btn.clicked.connect(self._log_selected_offlinetest_cmd)
        self.log_all_cmd_btn.clicked.connect(self._log_all_offlinetest_cmd)
        self.save_as_btn.clicked.connect(self._save_detection_json_as)
        self.table.itemDoubleClicked.connect(
            lambda _item: self._open_selected_runtime_view()
        )
        self.table.itemSelectionChanged.connect(self._on_row_selection_changed)

        self._refresh_scan_name_options()
        self._refresh_detection_version_options()

    def _browse_dll(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("Select DLL"),
            self.dll_path_edit.text().strip() or ".",
            self.tr("DLL Files (*.dll);;All Files (*)"),
        )
        if filename:
            self.dll_path_edit.setText(filename)

    def _browse_local_json_dir(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            self.tr("Select Local Json Folder"),
            self.local_json_dir_edit.text().strip() or ".",
            QtWidgets.QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            self.local_json_dir_edit.setText(folder)

    def _browse_json_file(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("Select Detection Json"),
            self.json_file_edit.text().strip() or ".",
            self.tr("Json Files (*.json);;All Files (*)"),
        )
        if filename:
            self.json_file_edit.setText(filename)

    def _scan_name_value(self) -> str:
        return self.scan_name_combo.currentText().strip()

    def _detection_version_value(self) -> str:
        return self.det_version_combo.currentText().strip()

    def _set_combo_items(self, combo: QtWidgets.QComboBox, items: List[str]):
        current = combo.currentText().strip()
        combo.blockSignals(True)
        combo.clear()
        for item in items:
            combo.addItem(item)
        if current:
            if combo.findText(current) < 0:
                combo.addItem(current)
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _refresh_scan_name_options(self):
        dat_home = self.dat_home_edit.text().strip()
        if not dat_home or not os.path.isdir(dat_home):
            return

        names = []
        scan_pattern = re.compile(r"^\d{4}_\d{2}_\d{2}\s\d{2}_\d{2}_\d{2}$")
        try:
            for year in os.scandir(dat_home):
                if not year.is_dir() or not re.match(r"^\d{4}$", year.name):
                    continue
                for month in os.scandir(year.path):
                    if not month.is_dir() or not re.match(r"^\d{2}$", month.name):
                        continue
                    for day in os.scandir(month.path):
                        if not day.is_dir() or not re.match(r"^\d{2}$", day.name):
                            continue
                        for scan in os.scandir(day.path):
                            if scan.is_dir() and scan_pattern.match(scan.name):
                                names.append(scan.name)
        except OSError:
            return

        unique_names = sorted(set(names), reverse=True)
        if unique_names:
            self._set_combo_items(self.scan_name_combo, unique_names)

    def _refresh_detection_version_options(self):
        dat_home = self.dat_home_edit.text().strip()
        scan_name = self._scan_name_value()
        if not dat_home or not scan_name:
            return

        match = re.match(
            r"(?P<year>\d{4})[-_ ](?P<month>\d{2})[-_ ](?P<day>\d{2})",
            scan_name,
        )
        if not match:
            return

        det_dir = os.path.join(
            dat_home,
            match.group("year"),
            match.group("month"),
            match.group("day"),
            scan_name,
            "detection",
        )
        if not os.path.isdir(det_dir):
            return

        versions = []
        try:
            for entry in os.scandir(det_dir):
                if entry.is_dir():
                    versions.append(entry.name)
        except OSError:
            return

        versions = sorted(set(versions))
        if versions:
            self._set_combo_items(self.det_version_combo, versions)

    def _load_session(self):
        self._scan_name = self._scan_name_value()
        dat_home = self.dat_home_edit.text().strip()
        self._dat_home = dat_home
        dll_path = self.dll_path_edit.text().strip()

        if not self._scan_name:
            self.meta_label.setText(self.tr("Scan name is required."))
            return

        if not os.path.isdir(dat_home):
            self.meta_label.setText(
                self.tr("DAT home does not exist: {0}").format(dat_home)
            )
            return

        self._reader = SickDataReaderGenerator(dll_path)
        reader = self._reader.generate(dat_home, self._scan_name)
        if reader is None:
            self.meta_label.setText(
                self.tr(
                    "Failed to load DAT reader or initialize scan handle. Details: {0}"
                ).format(self._reader.last_error or self.tr("Unknown error"))
            )
            return

        dim = reader.get_dim()
        cdim = reader.get_combined_dim()
        res = reader.get_resolution()
        off = reader.get_offset()
        tag = reader.get_tag()
        has_reflectance = reader.get_has_reflectance()
        version = reader.get_version()
        if dim:
            self._scan_y_start = int(dim[1])
            self._scan_height = int(dim[5])
        self._dat_reader = reader
        if cdim:
            self._combined_width = int(cdim[0])
            self._combined_height = int(cdim[1])

        json_path = self._resolve_json_path(dat_home, self._scan_name)
        if not json_path:
            self.meta_label.setText(self.tr("Unable to resolve detection json path."))
            return

        if not os.path.isfile(json_path):
            self.meta_label.setText(
                self.tr("Detection json does not exist: {0}").format(json_path)
            )
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as exc:
            self.meta_label.setText(
                self.tr("Failed to load detection json: {0}").format(str(exc))
            )
            return

        self._detection_json_data = self._extract_detection_data(payload)
        self._detection_payload = payload
        self._source_json_path = json_path
        self._extract_data_ids(self._detection_json_data)
        self._build_sub_type_index(self._detection_json_data)
        if not self._sub_type_keys:
            self.meta_label.setText(
                self.tr(
                    "Detection json loaded, but no *Info defect sections were found."
                )
            )
            return
        self._populate_type_combo()

        meta_lines = [
            self.tr("DAT loaded successfully."),
            self.tr("Reader Version: {0}").format(version or "N/A"),
            self.tr("Tag: {0}").format(tag or "N/A"),
            self.tr("Has Reflectance: {0}").format(str(has_reflectance)),
        ]
        if dim:
            meta_lines.append(self.tr("Dim: {0} x {1}").format(dim[4], dim[5]))
        if cdim:
            meta_lines.append(
                self.tr("Combined Dim: {0} x {1}").format(cdim[0], cdim[1])
            )
        if res:
            self._res_x_left = float(res[0])
            self._res_y_left = float(res[1]) if float(res[1]) != 0 else 1.0
            meta_lines.append(
                self.tr("Resolution L/R: ({0:.4f},{1:.4f}) / ({2:.4f},{3:.4f})").format(
                    res[0], res[1], res[2], res[3]
                )
            )
        if off:
            meta_lines.append(self.tr("Offset: ({0}, {1})").format(off[0], off[1]))
        meta_lines.append(self.tr("Detection Json: {0}").format(json_path))

        self.meta_label.setText("\n".join(meta_lines))

    def _resolve_json_path(self, dat_home: str, scan_name: str) -> Optional[str]:
        if self.use_json_file_check.isChecked():
            json_file = self.json_file_edit.text().strip()
            return json_file or None

        if self.use_local_json_check.isChecked():
            folder = self.local_json_dir_edit.text().strip()
            if not folder:
                return None
            return os.path.join(folder, f"global_{scan_name}.json")

        match = re.match(
            r"(?P<year>\d{4})[-_ ](?P<month>\d{2})[-_ ](?P<day>\d{2})",
            scan_name,
        )
        if not match:
            return None

        year = match.group("year")
        month = match.group("month")
        day = match.group("day")
        det_version = self._detection_version_value() or "v1.0.0.0"
        preferred_path = os.path.join(
            dat_home,
            year,
            month,
            day,
            scan_name,
            "detection",
            det_version,
            f"global_{scan_name}.json",
        )
        if os.path.isfile(preferred_path):
            return preferred_path

        detection_dir = os.path.join(
            dat_home,
            year,
            month,
            day,
            scan_name,
            "detection",
        )
        if os.path.isdir(detection_dir):
            expected_name = f"global_{scan_name}.json"
            for root, _dirs, files in os.walk(detection_dir):
                if expected_name in files:
                    return os.path.join(root, expected_name)

        return preferred_path

    def _suggest_default_paths(self):
        cwd = os.getcwd()
        candidates = [
            os.path.join(cwd, "ipas_dat_reader_dll.dll"),
            os.path.join(cwd, "..", "..", "..", "..", "..", "ManualInspection-master", "manualinspection", "src", "ipas_dat_reader_dll.dll"),
            os.path.join(cwd, "..", "..", "..", "..", "..", "alg_py_app_master_v4.7.3", "api", "ipas_dat_reader_dll.dll"),
        ]
        for candidate in candidates:
            abs_candidate = os.path.abspath(candidate)
            if os.path.isfile(abs_candidate):
                self.dll_path_edit.setText(abs_candidate)
                break

    def _extract_detection_data(self, payload: Dict) -> Dict:
        if "OFFLINETEST_VERSION" in payload:
            return payload

        lib_info = payload.get("LIB_INFO", {})
        if "ALGAPP_VERSION" in lib_info and "DETECTION_INFO" in payload:
            return payload["DETECTION_INFO"]

        return payload.get("DETECTION_INFO", payload)

    def _extract_data_ids(self, data: Dict):
        inspect_info = data.get("InspectInfo", {})
        data_ids = (
            inspect_info.get("DATA_ID")
            or inspect_info.get("data_id")
            or data.get("DATA_ID")
            or data.get("data_id")
        )
        if not data_ids or not isinstance(data_ids, list):
            self._detection_length = 5000
            self._non_overlap_length = 4500
            return

        try:
            self._detection_length = int(data_ids[0][1]) - int(data_ids[0][0])
            if len(data_ids) > 1:
                self._non_overlap_length = int(data_ids[0][1]) - int(data_ids[1][0])
            else:
                self._non_overlap_length = self._detection_length
        except Exception:
            self._detection_length = 5000
            self._non_overlap_length = 4500

    def _normalize(self, name: str) -> str:
        if name.endswith("ies"):
            return name[:-3] + "y"
        if name.endswith(("ches", "shes", "sses", "xes", "zes")):
            return name[:-2]
        if name.endswith("s") and not name.endswith("ss"):
            return name[:-1]
        return name

    def _build_sub_type_index(self, data: Dict):
        self._sub_type_keys.clear()
        for key, value in data.items():
            if not key.endswith("Info") or not isinstance(value, dict):
                continue

            all_count_keys = []
            info_lookup = {}
            self._sub_type_keys[key] = {}

            for sub_key, sub_value in value.items():
                if isinstance(sub_value, int) and sub_key.startswith("Numof"):
                    all_count_keys.append(sub_key)
                elif isinstance(sub_value, (dict, list)):
                    info_lookup[self._normalize(sub_key)] = sub_key

            for count_key in all_count_keys:
                defect_name = count_key[len("Numof") :]
                base = self._normalize(defect_name)
                info_key = info_lookup.get(base, "")
                self._sub_type_keys[key][defect_name] = {
                    "count_key": count_key,
                    "info_key": info_key,
                }

    def _populate_type_combo(self):
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        self.type_combo.addItems(sorted(self._sub_type_keys.keys()))
        self.type_combo.blockSignals(False)
        self._on_type_changed(self.type_combo.currentText())

    def _on_type_changed(self, type_name: str):
        self.subtype_combo.blockSignals(True)
        self.subtype_combo.clear()
        keys = self._sub_type_keys.get(type_name, {})
        for sub_type, info in sorted(keys.items()):
            count_key = info.get("count_key", "")
            count = self._detection_json_data.get(type_name, {}).get(count_key, 0)
            self.subtype_combo.addItem(f"{sub_type} ({count})", sub_type)
        self.subtype_combo.blockSignals(False)
        self._populate_rows()

    def _current_subtype(self) -> str:
        data = self.subtype_combo.currentData()
        if isinstance(data, str):
            return data
        text = self.subtype_combo.currentText()
        return text.split(" (")[0] if text else ""

    def _populate_rows(self):
        type_name = self.type_combo.currentText()
        sub_type = self._current_subtype()

        self._rows = self._build_rows(type_name, sub_type)
        self.table.setRowCount(len(self._rows))

        for row_idx, row in enumerate(self._rows):
            values = [
                row.index,
                row.y_start,
                row.y_end,
                row.merged_start,
            ]
            for col_idx, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(str(value))
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self.table.setItem(row_idx, col_idx, item)

        if self._rows:
            self.table.selectRow(0)
        else:
            self.selection_info_label.setText(
                self.tr("Selected Defect: none")
            )

    def _build_rows(self, type_name: str, sub_type: str) -> List[DefectRow]:
        if not type_name or not sub_type:
            return []

        type_data = self._detection_json_data.get(type_name)
        if not isinstance(type_data, dict):
            return []

        meta = self._sub_type_keys.get(type_name, {}).get(sub_type)
        if not meta:
            return []

        count_key = meta.get("count_key", "")
        info_key = meta.get("info_key", "")
        if not info_key:
            return []

        count = int(type_data.get(count_key, 0) or 0)
        defect_info = type_data.get(info_key, {})
        if not isinstance(defect_info, dict):
            return []

        rows: List[DefectRow] = []
        for idx in range(max(0, count)):
            y_start, y_end = self._get_y_range_for_index(defect_info, idx)
            if y_start is None or y_end is None:
                continue

            global_line = int(y_start + self._scan_y_start)
            merged_start = int(
                global_line // max(1, self._non_overlap_length)
            ) * max(1, self._non_overlap_length)
            bound_rects = self._extract_bound_rects_for_index(defect_info, idx)
            details = self._extract_defect_overlay_details(
                defect_info,
                idx,
                bound_rects,
            )
            rows.append(
                DefectRow(
                    type_name=type_name,
                    sub_type=sub_type,
                    index=idx,
                    y_start=int(y_start),
                    y_end=int(y_end),
                    merged_start=int(merged_start),
                    bound_rects=bound_rects,
                    details=details,
                )
            )
        return rows

    def _extract_defect_overlay_details(
        self,
        defect_info: Dict,
        idx: int,
        bound_rects: List[List[float]],
    ) -> Dict[str, Any]:
        details: Dict[str, Any] = {"BoundRect": bound_rects}

        for key, value in defect_info.items():
            if key == "BoundRect":
                continue

            selected = self._pick_defect_value(value, idx)
            if selected is None:
                continue

            if self._is_overlay_detail_key(key):
                details[key] = selected

        return details

    def _pick_defect_value(self, value: Any, idx: int) -> Optional[Any]:
        if isinstance(value, (list, tuple)):
            if 0 <= idx < len(value):
                return value[idx]
            return None

        if isinstance(value, dict):
            if idx in value:
                return value[idx]
            sidx = str(idx)
            if sidx in value:
                return value[sidx]
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        return None

    def _is_overlay_detail_key(self, key: str) -> bool:
        key_norm = re.sub(r"[^a-z0-9]", "", key.lower())
        important_tokens = (
            "avgdepth",
            "avgwidth",
            "boundrect",
            "xgboostid",
            "depth",
            "width",
            "height",
            "area",
            "score",
            "conf",
            "id",
            "rect",
            "bbox",
            "angle",
            "severity",
        )
        return any(token in key_norm for token in important_tokens)

    def _extract_bound_rects_for_index(
        self, defect_info: Dict, idx: int
    ) -> List[List[float]]:
        bound_rect = defect_info.get("BoundRect")
        if not isinstance(bound_rect, list) or idx >= len(bound_rect):
            return []

        entry = bound_rect[idx]
        if isinstance(entry, list) and entry and isinstance(entry[0], (list, tuple)):
            rects = entry
        else:
            rects = [entry]

        result = []
        for rect in rects:
            if not isinstance(rect, (list, tuple)):
                continue
            if len(rect) not in (4, 5):
                continue
            try:
                result.append([float(v) for v in rect])
            except (TypeError, ValueError):
                continue
        return result

    def _get_y_range_for_index(
        self, defect_info: Dict, idx: int
    ) -> Tuple[Optional[float], Optional[float]]:
        bound_rect = defect_info.get("BoundRect")
        if not isinstance(bound_rect, list) or idx >= len(bound_rect):
            return None, None

        entry = bound_rect[idx]
        rects = []
        if isinstance(entry, list) and entry and isinstance(entry[0], (list, tuple)):
            rects = list(entry)
        else:
            rects = [entry]

        y_starts = []
        y_ends = []
        for rect in rects:
            rng = self._rect_y_range(rect)
            if rng is None:
                continue
            y_starts.append(rng[0])
            y_ends.append(rng[1])

        if not y_starts:
            return None, None
        return min(y_starts), max(y_ends)

    def _rect_y_range(self, rect) -> Optional[Tuple[float, float]]:
        if not isinstance(rect, (list, tuple)):
            return None

        if len(rect) == 4:
            y = float(rect[1])
            h = float(rect[3])
            return y, y + h

        if len(rect) == 5:
            # For rotated rects, treat [x, y, w, h, angle] as center format.
            cy = float(rect[1])
            h = float(rect[3])
            return cy - h / 2.0, cy + h / 2.0

        return None

    def _selected_row(self) -> Optional[DefectRow]:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rows):
            return None
        return self._rows[row]

    def _emit_jump(self):
        self._open_selected_runtime_view()

    def _emit_front_cam(self):
        row = self._selected_row()
        if row is None:
            return
        self.open_front_cam_requested.emit(
            self._scan_name,
            row.merged_start,
            self._dat_home,
        )

    def _open_selected_runtime_view(self):
        row = self._selected_row()
        if row is None:
            self.meta_label.setText(self.tr("Please select a defect row first."))
            return

        if self._runtime_preview_dialog is None:
            self._runtime_preview_dialog = QtWidgets.QDialog(self)
            self._runtime_preview_dialog.setWindowTitle(
                self.tr("Runtime DAT Defect View")
            )
            self._runtime_preview_dialog.resize(1400, 860)
            layout = QtWidgets.QVBoxLayout(self._runtime_preview_dialog)
            self._runtime_preview_info_label = QtWidgets.QLabel()
            self._runtime_preview_info_label.setWordWrap(True)
            layout.addWidget(self._runtime_preview_info_label)

            # Keep very tall rendered images navigable via scroll bars.
            self._runtime_preview_scroll = QtWidgets.QScrollArea()
            self._runtime_preview_scroll.setWidgetResizable(False)
            self._runtime_preview_scroll.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            self._runtime_preview_scroll.setStyleSheet(
                "background-color: #1e1e1e;"
            )

            self._runtime_preview_label = QtWidgets.QLabel()
            self._runtime_preview_label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            self._runtime_preview_label.setMinimumSize(1, 1)
            self._runtime_preview_scroll.setWidget(self._runtime_preview_label)
            layout.addWidget(self._runtime_preview_scroll)

        pixmap = self._build_row_preview_pixmap(
            row,
            1000,
            800,
            use_original_size=True,
        )
        if pixmap is None:
            self.meta_label.setText(self.tr("Unable to render runtime DAT view."))
            return

        if self._runtime_preview_info_label is not None:
            self._runtime_preview_info_label.setText(
                self.tr("Runtime DAT image size: {0} x {1}").format(
                    pixmap.width(), pixmap.height()
                )
            )
        self._runtime_preview_label.setPixmap(pixmap)
        self._runtime_preview_label.setFixedSize(pixmap.size())
        self._runtime_last_pixmap = pixmap
        self._runtime_preview_dialog.show()
        self._runtime_preview_dialog.raise_()
        self._runtime_preview_dialog.activateWindow()

    def _get_region_for_row(self, row: DefectRow) -> Tuple[int, int]:
        region_margin = 200
        region_global_start = int(
            max(self._scan_y_start, row.y_start + self._scan_y_start - region_margin)
        )
        region_global_end = int(row.y_end + self._scan_y_start + region_margin)
        if self._scan_height > 0:
            scan_global_end = self._scan_y_start + self._scan_height
            region_global_end = min(region_global_end, scan_global_end)
        region_height = max(64, region_global_end - region_global_start)
        return region_global_start, region_height

    def _build_offlinetest_cmd(self, merged_start: int) -> str:
        start_line = int(merged_start)
        end_line = int(start_line + self._detection_length)
        return (
            f'"OfflineTest.exe" "{self._dat_home}" "{self._scan_name}" '
            f"1 1 {start_line} {end_line} 1 NULL 0 1"
        )

    def _artifact_output_dir(self) -> str:
        """Keep exports in an outer folder rather than current CWD."""
        dll_path = self.dll_path_edit.text().strip()
        if dll_path:
            abs_dll = os.path.abspath(dll_path)
            dll_dir = os.path.dirname(abs_dll)
            # If DLL is in a src-like folder, export one level above.
            leaf = os.path.basename(dll_dir).lower()
            if leaf in {"src", "api", "bin", "build", "dist"}:
                parent_dir = os.path.dirname(dll_dir)
                if parent_dir and os.path.isdir(parent_dir):
                    return parent_dir
            if os.path.isdir(dll_dir):
                return dll_dir

        # Fallback to workspace outer folder for this module.
        return os.path.abspath(os.path.join(os.getcwd(), ".."))

    def _cmd_log_path(self) -> str:
        return os.path.join(
            self._artifact_output_dir(),
            "OfflineTest_Exe_Log_Cmd.txt",
        )

    def _append_cmd_log(self, lines: List[str]):
        log_path = self._cmd_log_path()
        with open(log_path, "a", encoding="utf-8") as fp:
            for line in lines:
                fp.write(line + "\n")
        self.meta_label.setText(
            self.tr("Saved command log: {0}").format(log_path)
        )

    def _log_selected_offlinetest_cmd(self):
        row = self._selected_row()
        if row is None:
            self.meta_label.setText(self.tr("Please select a defect row first."))
            return
        cmd = self._build_offlinetest_cmd(row.merged_start)
        self._append_cmd_log([cmd])

    def _log_all_offlinetest_cmd(self):
        if not self._rows:
            self.meta_label.setText(self.tr("No defects to export commands."))
            return
        lines = [self._current_subtype()]
        for row in self._rows:
            lines.append(self._build_offlinetest_cmd(row.merged_start))
        self._append_cmd_log(lines)

    def _save_detection_json_as(self):
        if not self._detection_payload:
            self.meta_label.setText(self.tr("No detection json is loaded."))
            return

        default_path = os.path.join(
            self._artifact_output_dir(),
            "new_result.json",
        )
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self.tr("Save Detection Json As"),
            default_path,
            self.tr("Json Files (*.json);;All Files (*)"),
        )
        if not filename:
            return
        try:
            with open(filename, "w", encoding="utf-8") as fp:
                json.dump(self._detection_payload, fp, indent=4)
        except Exception as exc:
            self.meta_label.setText(
                self.tr("Failed to save json: {0}").format(str(exc))
            )
            return
        self.meta_label.setText(
            self.tr("Saved json: {0}").format(os.path.abspath(filename))
        )

    def _on_row_selection_changed(self):
        row = self._selected_row()
        if row is None:
            return
        self.selection_info_label.setText(
            self.tr(
                "Selected Defect: type={0}, sub_type={1}, idx={2}, y=({3},{4}), merged_start={5}, boxes={6}"
            ).format(
                row.type_name,
                row.sub_type,
                row.index,
                row.y_start,
                row.y_end,
                row.merged_start,
                len(row.bound_rects),
            )
        )

    def _build_row_preview_pixmap(
        self,
        row: DefectRow,
        canvas_w: int,
        canvas_h: int,
        use_original_size: bool = False,
    ) -> Optional[QtGui.QPixmap]:
        canvas_w = max(320, int(canvas_w))
        canvas_h = max(180, int(canvas_h))

        region_global_start, region_height = self._get_region_for_row(row)

        data_width = self._combined_width if self._combined_width > 0 else 2048
        image = self._read_dat_preview_image(
            region_global_start,
            data_width,
            region_height,
        )
        if image is None:
            image = QtGui.QImage(data_width, region_height, QtGui.QImage.Format.Format_RGB888)
            image.fill(QtGui.QColor("#2b2b2b"))

        base_pixmap = QtGui.QPixmap.fromImage(image)
        target_w = canvas_w
        target_h = canvas_h
        if use_original_size:
            target_w = 1000
            ratio = self._res_x_left / (self._res_y_left or 1.0)
            # Mirror original behavior: fixed width + resolution-corrected height.
            target_h = int(
                image.height() * target_w / max(1, image.width()) * ratio
            )
            target_h = max(1, target_h)
            # Guard against extreme heights (e.g., rutting) that are impractical to display.
            target_h = min(target_h, 5000)

        scaled = base_pixmap.scaled(
            target_w,
            target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        composed = QtGui.QPixmap(target_w, target_h)
        composed.fill(QtGui.QColor("#1e1e1e"))
        painter = QtGui.QPainter(composed)
        offset_x = (target_w - scaled.width()) // 2
        offset_y = (target_h - scaled.height()) // 2
        painter.drawPixmap(offset_x, offset_y, scaled)

        sx = scaled.width() / max(1, image.width())
        sy = scaled.height() / max(1, image.height())
        pen = QtGui.QPen(QtGui.QColor("#ff4d4f"))
        pen.setWidth(2)
        painter.setPen(pen)

        mapped_boxes = []
        for box_idx, rect in enumerate(row.bound_rects):
            mapped = self._map_rect_to_region(
                rect,
                region_global_start,
                row,
            )
            if mapped is None:
                continue
            rx, ry, rw, rh = mapped
            x = int(offset_x + rx * sx)
            y = int(offset_y + ry * sy)
            w = max(1, int(rw * sx))
            h = max(1, int(rh * sy))
            painter.drawRect(x, y, w, h)
            mapped_boxes.append((box_idx, x, y, w, h, rect))

        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)

        # Header information overlaid on top-left of rendered depth image.
        info_lines = [
            f"Scan: {self._scan_name}",
            f"Type/SubType: {row.type_name}/{row.sub_type}",
            f"Defect: idx={row.index}",
            f"Y local=({row.y_start}, {row.y_end}) global=({row.y_start + self._scan_y_start}, {row.y_end + self._scan_y_start})",
            f"MergedStart={row.merged_start} RegionStart={region_global_start} RegionHeight={region_height}",
            f"Boxes={len(mapped_boxes)}",
        ]
        info_lines.extend(self._format_overlay_details(getattr(row, "details", {})))

        fm = QtGui.QFontMetrics(painter.font())
        pad = 8
        line_h = fm.height() + 2

        # Keep overlay text inside the visible image area.
        panel_left = offset_x + 8
        panel_top = offset_y + 8
        panel_right = offset_x + scaled.width() - 8
        panel_bottom = offset_y + scaled.height() - 8
        if panel_right <= panel_left + 80 or panel_bottom <= panel_top + 40:
            panel_left = 8
            panel_top = 8
            panel_right = target_w - 8
            panel_bottom = target_h - 8

        max_text_w = max(80, panel_right - panel_left - 2 * pad)
        max_lines = max(1, (panel_bottom - panel_top - 2 * pad) // line_h)

        visible_lines = []
        for line in info_lines:
            visible_lines.append(
                fm.elidedText(
                    line,
                    Qt.TextElideMode.ElideRight,
                    max_text_w,
                )
            )

        if len(visible_lines) > max_lines:
            remain = len(visible_lines) - max_lines + 1
            visible_lines = visible_lines[: max(0, max_lines - 1)]
            visible_lines.append(f"... +{remain} more")

        block_w = min(
            panel_right - panel_left,
            max(fm.horizontalAdvance(line) for line in visible_lines) + 2 * pad,
        )
        block_h = line_h * len(visible_lines) + 2 * pad
        block_x = panel_left
        block_y = panel_top

        painter.fillRect(
            QtCore.QRect(block_x, block_y, block_w, block_h),
            QtGui.QColor(0, 0, 0, 140),
        )
        painter.setPen(QtGui.QColor("#f4f4f4"))
        for i, line in enumerate(visible_lines):
            painter.drawText(
                block_x + pad,
                block_y + pad + (i + 1) * line_h - 3,
                line,
            )

        # Draw per-box index and source coordinates near each rectangle.
        painter.setPen(QtGui.QColor("#ffd666"))
        for box_idx, x, y, _w, _h, rect in mapped_boxes:
            coord_text = (
                f"#{box_idx} rect={int(rect[0])},{int(rect[1])},{int(rect[2])},{int(rect[3])}"
                if len(rect) >= 4
                else f"#{box_idx}"
            )
            coord_text = fm.elidedText(
                coord_text,
                Qt.TextElideMode.ElideRight,
                max(40, target_w - 12),
            )
            text_w = fm.horizontalAdvance(coord_text)
            text_x = min(max(4, x), max(4, target_w - text_w - 4))
            text_y = min(max(14, y - 4), max(14, target_h - 4))
            painter.drawText(text_x, text_y, coord_text)

        painter.end()
        return composed

    def _format_overlay_details(self, details: Dict[str, Any]) -> List[str]:
        if not isinstance(details, dict) or not details:
            return []

        # Show important fields first and keep list concise for on-image readability.
        preferred_keys = [
            "AvgDepth",
            "AvgWidth",
            "BoundRect",
            "XGBoostId",
            "avgDepth",
            "avgWidth",
            "boundRect",
            "xgboostId",
        ]
        output: List[str] = []
        seen = set()

        for key in preferred_keys:
            if key not in details:
                continue
            output.append(self._format_overlay_detail_line(key, details.get(key)))
            seen.add(key)
            if len(output) >= 8:
                return output

        for key in sorted(details.keys()):
            if key in seen:
                continue
            if key == "BoundRect":
                continue
            output.append(self._format_overlay_detail_line(key, details.get(key)))
            if len(output) >= 8:
                break

        return output

    def _format_overlay_detail_line(self, key: str, value: Any) -> str:
        text = self._short_value_text(value)
        if len(text) > 110:
            text = text[:110] + "..."
        return f"{key}: {text}"

    def _short_value_text(self, value: Any) -> str:
        if isinstance(value, list):
            if value and isinstance(value[0], list):
                # BoundRect-like structure: show first rectangle and count.
                first = value[0]
                first_str = ", ".join(str(int(v) if isinstance(v, float) and v.is_integer() else v) for v in first[:5])
                suffix = ""
                if len(value) > 1:
                    suffix = f" (+{len(value) - 1} more)"
                return f"[{first_str}]{suffix}"
            text = ", ".join(str(v) for v in value[:8])
            if len(value) > 8:
                text += f", ... (+{len(value) - 8})"
            return text

        if isinstance(value, dict):
            items = list(value.items())[:4]
            text = ", ".join(f"{k}={v}" for k, v in items)
            if len(value) > 4:
                text += f", ... (+{len(value) - 4})"
            return text

        return str(value)

    def _read_dat_preview_image(self, start_y: int, width: int, height: int):
        if self._dat_reader is None:
            return None
        raw = self._dat_reader.get_combined_relative_layer(
            0,
            int(start_y),
            int(width),
            int(height),
            False,
        )
        if raw is None:
            return None

        qimg = QtGui.QImage(raw, width, height, width, QtGui.QImage.Format.Format_Grayscale8)
        return qimg.copy().convertToFormat(QtGui.QImage.Format.Format_RGB888)

    def _map_rect_to_region(
        self,
        rect: List[float],
        region_global_start: int,
        row: DefectRow,
    ) -> Optional[Tuple[float, float, float, float]]:
        if len(rect) == 4:
            x = rect[0]
            y = rect[1]
            w = rect[2]
            h = rect[3]
        elif len(rect) == 5:
            x = rect[0] - rect[2] / 2.0
            y = rect[1] - rect[3] / 2.0
            w = rect[2]
            h = rect[3]
        else:
            return None

        # Detection y is local to scan; preview region y is global.
        global_y = y + self._scan_y_start
        local_y = global_y - region_global_start
        if h <= 0 or w <= 0:
            return None
        return x, local_y, w, h

