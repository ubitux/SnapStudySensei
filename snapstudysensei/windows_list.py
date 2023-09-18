import xcffib
import xcffib.xproto


class WindowsList:
    def __init__(self):
        self._xcb = xcffib.connect()
        self._atom_client_list = self._xcb_get_atom("_NET_CLIENT_LIST")
        self._atom_wm_name = self._xcb_get_atom("_NET_WM_NAME")

    def _xcb_get_atom(self, name: str) -> int:
        return self._xcb.core.InternAtom(only_if_exists=False, name=name, name_len=len(name)).reply().atom

    def _xcb_get_prop(self, wid: int, prop: int):
        return self._xcb.core.GetProperty(
            delete=False,
            window=wid,
            property=prop,
            type=xcffib.xproto.GetPropertyType.Any,
            long_offset=0,
            long_length=0xFFFFFFFF,
        ).reply()

    def __call__(self) -> dict[int, tuple[str, bool]]:
        windows = {}
        for screen in self._xcb.get_setup().roots:
            children = self._xcb_get_prop(screen.root, self._atom_client_list).value.to_atoms()
            for wid in children:
                window_attrs = self._xcb.core.GetWindowAttributes(wid).reply()
                viewable = window_attrs.map_state == xcffib.xproto.MapState.Viewable
                window_title = self._xcb_get_prop(wid, self._atom_wm_name).value.to_utf8()
                windows[wid] = (window_title, viewable)
        return windows
