"""The API entries, one module per area; ALL lists every entry in order."""
from api.spec import core, data, system, hardware, display, network, storage, tools, ext_esp32, ext_ble, ext_matrix, host

MODULES = [core, data, system, hardware, display, network, storage, tools, ext_esp32, ext_ble, ext_matrix, host]
ALL = [e for m in MODULES for e in m.APIS]
