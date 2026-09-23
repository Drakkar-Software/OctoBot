#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

from pathlib import Path


class TestWebInterfaceLayouts:
    def test_layout_has_no_socket_io_script(self):
        web_interface_root = Path(__file__).resolve().parents[2]
        layout_paths = [
            web_interface_root / "templates" / "layout.html",
            web_interface_root / "advanced_templates" / "advanced_layout.html",
        ]
        for layout_path in layout_paths:
            content = layout_path.read_text(encoding="utf-8")
            assert "socket.io" not in content
